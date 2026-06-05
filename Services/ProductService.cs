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

        public async Task<(bool Exists, string Message, Product? Product)> CheckUrlAsync(string url)
        {
            string generatedHash = GenerateSHA256Hash(url);
            var existingProduct = await _productRepository.GetByUrlOrHashAsync(url, generatedHash);

            if (existingProduct != null)
            {
                return (true, "Ürün veritabanında mevcut.", existingProduct);
            }

            return (false, "Ürün bulunamadı, yeni analiz başlatılmalı.", null);
        }

        public async Task<(bool Success, string Message, int Count, object? Reviews)> GetReviewsForModelAsync(Guid productId)
        {
            var rawReviews = await _reviewRepository.GetCleanReviewsByProductIdAsync(productId);

            if (!rawReviews.Any())
            {
                return (false, "Bu ürüne ait yorum bulunamadı veya henüz scrape edilmedi.", 0, null);
            }

            // DTO projeksiyonunu (Select) Service katmanında yapıyoruz ki Controller ham veriyi görmesin
            var projectedReviews = rawReviews.Select(r => new 
            {
                r.Id,
                r.CleanText,
                r.OriginalRating
            }).ToList();

            return (true, "Başarılı", projectedReviews.Count, projectedReviews);
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

        public async Task<List<ProductDisplayDto>> GetPopularProductsAsync(int minClicks)
        {
            // Repository'ye kaç kayıt (limit) istediğimizi de parametre geçiyoruz (Clean Code)
            var popularProducts = await _productRepository.GetPopularProductsAsync(minClicks, limit: 20);

            return popularProducts.Select(p => new ProductDisplayDto
            {
                ProductName = p.ProductName,
                Category = p.Category,
                AvgOrjScore = p.AvgOrjScore,
                AvgModelScore = p.AvgModelScore,
                GuncelOzet = p.GuncelOzet
            }).ToList();
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