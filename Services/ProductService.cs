using Microsoft.Extensions.Configuration;
using System.Security.Cryptography;
using System.Text;
using LLM_Destekli_Ozetleme.Models.Entities;
using LLM_Destekli_Ozetleme.Models.DTOs;
using LLM_Destekli_Ozetleme.Repositories;
using System.Diagnostics; // Process sınıfı için zorunlu

namespace LLM_Destekli_Ozetleme.Services
{
    public class ProductService : IProductService
    {
        private readonly IProductRepository _productRepository;
        private readonly IReviewRepository _reviewRepository;

        private readonly IHttpClientFactory _httpClientFactory;
        private readonly IConfiguration _configuration; 

        // DbContext bitti, ambar görevlilerini (repositories) çağırıyoruz
        public ProductService(IProductRepository productRepository, IReviewRepository reviewRepository, IHttpClientFactory httpClientFactory, IConfiguration configuration)
        {
            _productRepository = productRepository;
            _reviewRepository = reviewRepository;
            _httpClientFactory = httpClientFactory;
            _configuration = configuration; 
        }

        public async Task<List<ProductListDto>> GetProductsAsync(ProductQueryParameters queryParams)
        {
            var products = await _productRepository.GetProductsAsync(queryParams);

            var productListDtos = products.Select(p => new ProductListDto
            {
                Id = p.Id,
                Name = p.ProductName,
                Category = p.Category ?? "Diğer",
                AverageRating = p.AvgOrjScore,
                ModelScore = p.AvgModelScore,
                ClickCount = p.ClickCount ?? 0,
                ImageUrl = p.ImageUrl
            }).ToList();

            return productListDtos;
        }

        public async Task<(bool NeedsRescrape, double MonthsPassed, string Message)> CheckProductStatusAsync(Guid productId)
        {
            var product = await _productRepository.GetByIdAsync(productId);
            
            if (product == null)
            {
                throw new Exception("Ürün bulunamadı.");
            }

            var referenceDate = product.CreatedAt ?? DateTime.UtcNow;
            var monthsPassed = (DateTime.UtcNow - referenceDate).TotalDays / 30.0;
            bool needsRescrape = monthsPassed > 3.0;

            string message = needsRescrape 
                ? "Ürün verileri 3 aydan eski. Yeniden scrape işlemi başlatılmalı." 
                : "Ürün verileri güncel. Tekrar scrape edilmesine gerek yok.";

            return (needsRescrape, Math.Round(monthsPassed, 1), message);
        }

        public async Task<(bool Success, string Message, Guid? ProductId)> Step1ScrapeAsync(string url)
        {
            try
            {
                string generatedHash = GenerateSHA256Hash(url);
                var existingProduct = await _productRepository.GetByUrlOrHashAsync(url, generatedHash);
                if (existingProduct != null)
                {
                    return (true, "Bu URL zaten veritabanında mevcut. Scrape işlemine gerek yok.", existingProduct.Id);
                }

                var client = _httpClientFactory.CreateClient();

                var pythonApiUrl = _configuration["PythonSettings:ApiBaseUrl"] ?? "http://localhost:8000";
                var requestUrl = $"{pythonApiUrl}/api/v1/extract";

                var response = await client.PostAsJsonAsync(requestUrl, new { url = url });

                if (!response.IsSuccessStatusCode)
                {
                    string errorContent = await response.Content.ReadAsStringAsync();
                    return (false, $"Python kazıma servisi hata döndürdü: {errorContent}", null);
                }

                var result = await response.Content.ReadFromJsonAsync<PythonApiResponse>();

                if (result != null && result.Status == "success" && Guid.TryParse(result.ProductId, out Guid newProductId))
                {
                    return (true, "Kazıma işlemi başarıyla tamamlandı ve ürün veritabanına eklendi.", newProductId);
                }

                return (false, "Python servisi işlemi tamamladı ancak geçerli bir Ürün ID'si döndüremedi.", null);
            }
            catch (Exception ex)
            {
                return (false, $"Kazıma servisi (Python) ile iletişim kurulamadı: {ex.Message}", null);
            }
        } 

        public async Task<(bool Success, string Message)> Step2ProcessAsync(Guid productId)
        {
            try
            {
                var client = _httpClientFactory.CreateClient();

                var pythonApiUrl = _configuration["PythonSettings:ApiBaseUrl"] ?? "http://localhost:8000";
                var requestUrl = $"{pythonApiUrl}/api/v1/score";

                var response = await client.PostAsJsonAsync(requestUrl, new { productId = productId });

                if (!response.IsSuccessStatusCode)
                {
                    string errorContent = await response.Content.ReadAsStringAsync();
                    return (false, $"Python puanlama servisi (BERTurk) hata döndürdü: {errorContent}");
                }

                var result = await response.Content.ReadFromJsonAsync<PythonApiResponse>();

                if (result != null && result.Status == "success")
                {
                    return (true, "Yorumlar BERTurk modeli ile başarıyla puanlandı ve veritabanına kaydedildi.");
                }

                return (false, "Python servisi puanlama işlemini tamamladı ancak başarısız bir durum kodu döndürdü.");
            }
            catch (Exception ex)
            {
                return (false, $"Puanlama servisi (Python) ile iletişim kurulamadı: {ex.Message}");
            }
        }

        public async Task<(bool Success, string Message)> Step3CategorizeAsync(Guid productId)
        {
            try
            {
                var client = _httpClientFactory.CreateClient();
                var pythonApiUrl = _configuration["PythonSettings:ApiBaseUrl"] ?? "http://localhost:8000";
                
                // Python tarafında bu işlem için /api/v1/categorize adında bir rota yazacağız
                var requestUrl = $"{pythonApiUrl}/api/v1/categorize";

                var response = await client.PostAsJsonAsync(requestUrl, new { productId = productId });

                if (!response.IsSuccessStatusCode)
                {
                    string errorContent = await response.Content.ReadAsStringAsync();
                    return (false, $"Python kategorizasyon servisi hata döndürdü: {errorContent}");
                }

                var result = await response.Content.ReadFromJsonAsync<PythonApiResponse>();

                if (result != null && result.Status == "success")
                {
                    return (true, "Yorumlar başarıyla niteliklerine (aspects) ayrıldı ve güncellendi.");
                }

                return (false, "Python servisi kategorizasyon işlemini tamamladı ancak başarısız bir durum kodu döndürdü.");
            }
            catch (Exception ex)
            {
                return (false, $"Kategorizasyon servisi (Python) ile iletişim kurulamadı: {ex.Message}");
            }
        }

        public async Task<(bool Success, string Message, string? Summary)> Step4SummarizeAsync(Guid productId)
        {
            try
            {
                var client = _httpClientFactory.CreateClient();
                var pythonApiUrl = _configuration["PythonSettings:ApiBaseUrl"] ?? "http://localhost:8000";
                
                // Python tarafında bu işlem için /api/v1/summarize adında bir rota yazacağız
                var requestUrl = $"{pythonApiUrl}/api/v1/summarize";

                var response = await client.PostAsJsonAsync(requestUrl, new { productId = productId });

                if (!response.IsSuccessStatusCode)
                {
                    string errorContent = await response.Content.ReadAsStringAsync();
                    return (false, $"Python LLM özetleme servisi hata döndürdü: {errorContent}", null);
                }

                var result = await response.Content.ReadFromJsonAsync<PythonApiResponse>();

                if (result != null && result.Status == "success")
                {
                    // İşlem başarılıysa hem DB'ye yazılmış oluyor hem de özeti frontend'e iletiyoruz
                    return (true, "Yapay zeka özeti başarıyla oluşturuldu.", result.Summary);
                }

                return (false, "Python servisi özetleme işlemini tamamladı ancak başarılı bir sonuç döndüremedi.", null);
            }
            catch (Exception ex)
            {
                return (false, $"Özetleme servisi (Python) ile iletişim kurulamadı: {ex.Message}", null);
            }
        }

        public async Task<ProductDetailDto?> GetProductDetailsByIdAsync(Guid productId, Guid? userId = null)
        {
            var product = await _productRepository.GetProductWithDetailsAsync(productId);
            if (product == null)
                return null;

            var latestHistory = product.SummaryHistories.FirstOrDefault();
            List<SourceReviewDto> sourceReviews = new();

            if (latestHistory != null && latestHistory.SourceReviewIds != null && latestHistory.SourceReviewIds.Any())
            {
                var reviews = await _productRepository.GetReviewsByIdsAsync(latestHistory.SourceReviewIds);
                sourceReviews = reviews.Select(r => new SourceReviewDto { Text = r.CleanText ?? r.RawText ?? string.Empty }).ToList();
            }

            bool isFavorited = false;

            if (userId.HasValue && userId != Guid.Empty)
            {
                isFavorited = await _productRepository.IsProductFavoritedByUserAsync(productId, userId.Value);
            }

            var dto = new ProductDetailDto
            {
                Id = product.Id,
                ProductName = product.ProductName,
                Platform = product.Platform,
                Category = product.Category,
                ImageUrl = product.ImageUrl,
                OriginalUrl = product.OriginalUrl,
                AvgOrjScore = product.AvgOrjScore,
                AvgModelScore = product.AvgModelScore,
                CeliskiScore = product.CeliskiScore, 
                GuncelOzet = product.GuncelOzet,
                
                CategoricalStats = product.CategoryStats.Select(cs => new CategoricalStatDto
                {
                    CategoryName = cs.CategoryName ?? "Genel",
                    CategoryModelAvgScore = cs.CategoryModelAvgScore,
                    CategorySummary = cs.CategorySummary
                }).ToList(),
                
                SourceReviews = sourceReviews,
                IsFavorited = isFavorited // Veritabanından gelen gerçek sonuç
            };

            return dto;
            
            
        }
        

        public async Task<(bool Success, string Message)> IncrementClickCountAsync(Guid productId)
        {
            try
            {
                var result = await _productRepository.IncrementClickCountAsync(productId);
                
                if (!result)
                {
                    return (false, "Ürün bulunamadı veya tıklama sayısı güncellenemedi.");
                }

                return (true, "Ürün tıklama sayısı başarıyla arttırıldı.");
            }
            catch (Exception ex)
            {
                return (false, $"Tıklama sayısı arttırılırken sistem hatası oluştu: {ex.Message}");
            }
        }

        public async Task<(bool Success, string Message, bool IsSaved)> ToggleProductSaveAsync(Guid userId, Guid productId)
        {
            try
            {
                var product = await _productRepository.GetByIdAsync(productId);
                if (product == null) return (false, "Ürün bulunamadı.", false);

                var interaction = await _productRepository.GetUserInteractionAsync(userId, productId);

                if (interaction == null)
                {
                    interaction = new UserProductInteraction
                    {
                        UserId = userId,
                        ProductId = productId,
                        IsSaved = true,
                        CreatedAt = DateTime.UtcNow
                    };
                }
                else
                {
                    interaction.IsSaved = !interaction.IsSaved;
                }

                var result = await _productRepository.SaveUserInteractionAsync(interaction);

                if (result)
                {
                    // Değişkeni if bloğunun içinde oluşturup anında return ediyoruz. Sorunsuz çalışacaktır.
                    string statusMsg = interaction.IsSaved ? "Ürün favorilere eklendi." : "Ürün favorilerden çıkarıldı.";
                    return (true, statusMsg, interaction.IsSaved);
                }

                return (false, "İşlem sırasında veritabanı hatası oluştu.", false);
            }
            catch (Exception ex)
            {
                return (false, $"Favori işlemi başarısız: {ex.Message}", false);
            }
        }

        public async Task<(bool Success, string Message)> RateSummaryAsync(Guid userId, Guid productId, int rating)
        {
            // 1. Güvenlik ve İş Kuralları: Puan 1 ile 5 arasında olmalıdır
            if (rating < 1 || rating > 5)
            {
                return (false, "Geçersiz puan! Değerlendirme 1 ile 5 arasında olmalıdır.");
            }

            try
            {
                // 2. Ürün gerçekten var mı kontrolü
                var product = await _productRepository.GetByIdAsync(productId);
                if (product == null) return (false, "Ürün bulunamadı.");

                // 3. Kullanıcının bu ürünle daha önce bir etkileşimi var mı?
                var interaction = await _productRepository.GetUserInteractionAsync(userId, productId);

                if (interaction == null)
                {
                    // Eğer hiç favoriye falan almamışsa, doğrudan puan vererek ilk etkileşimi başlatıyor
                    interaction = new UserProductInteraction
                    {
                        UserId = userId,
                        ProductId = productId,
                        SummaryRating = rating,
                        IsSaved = false, // Varsayılan değer
                        CreatedAt = DateTime.UtcNow
                    };
                }
                else
                {
                    // Daha önce favoriye almış veya işlem yapmış, sadece puanı güncelliyoruz
                    interaction.SummaryRating = rating;
                }

                // 4. Veritabanına kaydet (Eski yazdığımız repository metodunu tekrar kullanıyoruz!)
                var result = await _productRepository.SaveUserInteractionAsync(interaction);

                if (result)
                {
                    return (true, "Özet değerlendirmeniz başarıyla kaydedildi. Geri bildiriminiz için teşekkürler!");
                }

                return (false, "İşlem sırasında veritabanı hatası oluştu.");
            }
            catch (Exception ex)
            {
                return (false, $"Değerlendirme işlemi başarısız: {ex.Message}");
            }
        }
        private string GenerateSHA256Hash(string rawData)
        {
            using (SHA256 sha256Hash = SHA256.Create())
            {
                byte[] bytes = sha256Hash.ComputeHash(Encoding.UTF8.GetBytes(rawData));
                StringBuilder builder = new StringBuilder();
                for (int i = 0; i < bytes.Length; i++)
                {
                    builder.Append(bytes[i].ToString("x2"));
                }
                return builder.ToString();
            }
        }

    }

    public class PythonApiResponse
    {
        public string Status { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
        public string ProductId { get; set; } = string.Empty;
        public string? Summary { get; set; }
    }
}