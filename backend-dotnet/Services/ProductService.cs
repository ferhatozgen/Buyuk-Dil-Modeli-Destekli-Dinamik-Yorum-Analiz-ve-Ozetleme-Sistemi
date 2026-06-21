using Microsoft.Extensions.Configuration;
using Microsoft.EntityFrameworkCore;
using System.Security.Cryptography;
using System.Text;
using LLM_Destekli_Ozetleme.Models.Entities;
using LLM_Destekli_Ozetleme.Models.DTOs;
using LLM_Destekli_Ozetleme.Repositories;

namespace LLM_Destekli_Ozetleme.Services
{
    public class ProductService : IProductService
    {
        private readonly IProductRepository _productRepository;
        private readonly IReviewRepository _reviewRepository;
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly IConfiguration _configuration; 

        public ProductService(IProductRepository productRepository, IReviewRepository reviewRepository, IHttpClientFactory httpClientFactory, IConfiguration configuration)
        {
            _productRepository = productRepository;
            _reviewRepository = reviewRepository;
            _httpClientFactory = httpClientFactory;
            _configuration = configuration; 
        }

        public async Task<List<ProductListDto>> GetProductsAsync(ProductQueryParameters queryParams, Guid? userId = null)
        {
            var products = await _productRepository.GetProductsAsync(queryParams);
            var productListDtos = new List<ProductListDto>();

            foreach (var product in products)
            {
                bool isFavorited = false;

                if (userId.HasValue)
                {
                    isFavorited = await _productRepository.IsProductFavoritedByUserAsync(product.Id, userId.Value);
                }

                productListDtos.Add(new ProductListDto
                {
                    Id = product.Id,
                    Name = product.ProductName,
                    Category = product.Category ?? "Diğer",
                    ModelScore = product.AvgModelScore,
                    ClickCount = product.ClickCount ?? 0,
                    ImageUrl = product.ImageUrl,
                    PlatformName = product.Platform, 
                    IsFavorited = isFavorited
                });
            }

            return productListDtos;
        }

        public async Task<(bool NeedsRescrape, double MonthsPassed, string Message)> CheckProductStatusAsync(Guid productId)
        {
            var product = await _productRepository.GetByIdAsync(productId);
            
            if (product == null)
            {
                throw new Exception("Ürün bulunamadı.");
            }

            var referenceDate = product.CreatedAt! ?? DateTime.UtcNow;
            var monthsPassed = (DateTime.UtcNow - referenceDate).TotalDays / 30.0;
            bool needsRescrape = monthsPassed > 3.0;

            string message = needsRescrape 
                ? "Ürün verileri 3 aydan eski. Yeniden scrape işlemi başlatılmalı." 
                : "Ürün verileri güncel. Tekrar scrape edilmesine gerek yok.";

            return (needsRescrape, Math.Round(monthsPassed, 1), message);
        }

        public async Task<ProductDetailDto?> GetProductDetailsByIdAsync(Guid productId, Guid? userId = null)
        {
            var product = await _productRepository.GetProductWithDetailsAsync(productId);
            if (product == null)
                return null;

            var latestHistory = product.SummaryHistories?.FirstOrDefault();
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
                
                CategoricalStats = product.CategoryStats?.Select(cs => new CategoricalStatDto
                {
                    CategoryName = cs.CategoryName ?? "Genel",
                    CategoryModelAvgScore = cs.CategoryModelAvgScore,
                    CategorySummary = cs.CategorySummary
                }).ToList() ?? new List<CategoricalStatDto>(),
                
                SourceReviews = sourceReviews,
                IsFavorited = isFavorited
            };

            return dto;
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
                    return (true, "Yapay zeka özeti başarıyla oluşturuldu.", result.Summary);
                }

                return (false, "Python servisi özetleme işlemini tamamladı ancak başarılı bir sonuç döndüremedi.", null);
            }
            catch (Exception ex)
            {
                return (false, $"Özetleme servisi (Python) ile iletişim kurulamadı: {ex.Message}", null);
            }
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
            if (rating < 1 || rating > 5)
            {
                return (false, "Geçersiz puan! Değerlendirme 1 ile 5 arasında olmalıdır.");
            }

            try
            {
                var product = await _productRepository.GetByIdAsync(productId);
                if (product == null) return (false, "Ürün bulunamadı.");

                var interaction = await _productRepository.GetUserInteractionAsync(userId, productId);

                if (interaction == null)
                {
                    interaction = new UserProductInteraction
                    {
                        UserId = userId,
                        ProductId = productId,
                        SummaryRating = rating,
                        IsSaved = false,
                        CreatedAt = DateTime.UtcNow
                    };
                }
                else
                {
                    interaction.SummaryRating = rating;
                }

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

        public async Task<ProductTrendDto> GetProductTrendAsync(Guid productId)
        {
            // 1. Veritabanından ürüne ait puanlanmış VE gerçek tarihi (ReviewedAt) olan yorumları çekiyoruz
            var reviews = await _reviewRepository.GetQueryable()
                .Where(r => r.ProductId == productId && r.PredictedScore != null && r.ReviewedAt != null)
                .ToListAsync();

            if (!reviews.Any())
                return new ProductTrendDto { ProductId = productId, PeriodType = "NoData" };

            // 2. Sahte Tarih Filtresi (2000 yılından eski olanları eledik)
            var validReviews = reviews.Where(r => r.ReviewedAt!.Value.Year > 2000).ToList();

            if (!validReviews.Any())
                return new ProductTrendDto { ProductId = productId, PeriodType = "NoData" };

            var minDate = validReviews.Min(r => r.ReviewedAt!.Value);
            var maxDate = validReviews.Max(r => r.ReviewedAt!.Value);
            var totalDays = (maxDate - minDate).TotalDays;

            var result = new ProductTrendDto { ProductId = productId };

            // 3. STRING BAZLI GRUPLAMA MANTIĞI
            IEnumerable<IGrouping<string, Review>> groupedReviews;

            if (totalDays <= 30 || totalDays <= 365)
            {
                result.PeriodType = totalDays <= 30 ? "SinglePoint" : "Monthly";
                // Ay bazlı gruplama ("2026-05" formatında)
                groupedReviews = validReviews.GroupBy(r => r.ReviewedAt!.Value.ToString("yyyy-MM"));
            }
            else if (totalDays <= 1095)
            {
                result.PeriodType = "Quarterly";
                // 3 Aylık gruplama ("2026-Q2" formatında)
                groupedReviews = validReviews.GroupBy(r => $"{r.ReviewedAt!.Value.Year}-Q{((r.ReviewedAt!.Value.Month - 1) / 3) + 1}");
            }
            else
            {
                result.PeriodType = "Yearly";
                // Yıl bazlı gruplama ("2026" formatında)
                groupedReviews = validReviews.GroupBy(r => r.ReviewedAt!.Value.ToString("yyyy"));
            }

            // 4. Sonuçları DTO'ya eşle ve tarih sırasına göre diz
            foreach (var group in groupedReviews.OrderBy(g => g.Key))
            {
                result.Trends.Add(new TrendDataPointDto
                {
                    PeriodLabel = group.Key,
                    StartDate = group.First().ReviewedAt!.Value, 
                    AverageScore = Math.Round(group.Average(r => (double)r.PredictedScore!), 2),
                    ReviewCount = group.Count()
                });
            }
            // 5. SEYREK VERİLERİ BİRLEŞTİRME (DATA SMOOTHING)
            int minReviewThreshold = 3; // 3'ten az yorumu olan periyotları hedefe kat
            for (int i = 0; i < result.Trends.Count; i++)
            {
                // Eğer yorum sayısı eşiğin altındaysa ve listede birleşebilecek başka bir eleman varsa
                if (result.Trends[i].ReviewCount < minReviewThreshold && result.Trends.Count > 1)
                {
                    var current = result.Trends[i];
                    
                    // Eğer son eleman değilse bir sonrakine (geleceğe), son elemansa bir öncekine (geçmişe) ekle
                    int targetIndex = (i < result.Trends.Count - 1) ? i + 1 : i - 1;
                    var target = result.Trends[targetIndex];

                    // Ağırlıklı ortalama hesapla: ((Puan1 * Sayı1) + (Puan2 * Sayı2)) / ToplamSayı
                    double totalScore = (target.AverageScore * target.ReviewCount) + (current.AverageScore * current.ReviewCount);
                    target.ReviewCount += current.ReviewCount;
                    target.AverageScore = Math.Round(totalScore / target.ReviewCount, 2);

                    // Grafik X ekseni için etiketleri birleştir (Örn: "2010 & 2011")
                    if (i < result.Trends.Count - 1) 
                        target.PeriodLabel = current.PeriodLabel + " & " + target.PeriodLabel;
                    else 
                        target.PeriodLabel = target.PeriodLabel + " & " + current.PeriodLabel;

                    // Zayıf periyodu listeden sil
                    result.Trends.RemoveAt(i);
                    i--; // Listeden eleman sildiğimiz için kaymayı önlemek adına indeksi bir geri alıyoruz
                }
            }

            return result;
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
