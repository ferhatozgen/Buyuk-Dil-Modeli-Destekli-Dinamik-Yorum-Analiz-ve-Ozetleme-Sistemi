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
        private readonly IConfiguration _configuration; 

        // DbContext bitti, ambar görevlilerini (repositories) çağırıyoruz
        public ProductService(IProductRepository productRepository, IReviewRepository reviewRepository, IConfiguration configuration)
        {
            _productRepository = productRepository;
            _reviewRepository = reviewRepository;
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

        public async Task<(bool Success, string Message, Guid? ProductId)> ScrapeAndPredictAsync(string url)
        {
            try
            {
                // 1. Önce bu link daha önce işlenmiş mi kontrol et
                string generatedHash = GenerateSHA256Hash(url);
                var existingProduct = await _productRepository.GetByUrlOrHashAsync(url, generatedHash);

                if (existingProduct != null)
                {
                    return (true, "Bu ürün zaten veritabanında mevcut.", existingProduct.Id);
                }

                // 2. Python Yapılandırma Ayarları (api_runner.py'yi hedefliyoruz)
                var pythonExe = _configuration["PythonSettings:PythonExePath"] ?? throw new InvalidOperationException("Python exe yolu appsettings.json dosyasında bulunamadı.");
                var pythonScript = _configuration["PythonSettings:ScriptPath"] ?? throw new InvalidOperationException("Python script yolu appsettings.json dosyasında bulunamadı.");

                var startInfo = new ProcessStartInfo
                {
                    FileName = pythonExe,
                    // DİKKAT: Burada pythonScript ve url parametrelerini doğru formatta gönderiyoruz
                    Arguments = $"\"{pythonScript}\" --url \"{url}\"", 
                    UseShellExecute = false,
                    RedirectStandardOutput = true, // Python print'lerini yakala
                    RedirectStandardError = true,  // Python exception'larını yakala
                    CreateNoWindow = true
                };

                // 3. İşlemi Başlat ve Zaman Aşımı (Timeout) Koruması Ekle
                using (var process = Process.Start(startInfo))
                {
                    if (process == null)
                        return (false, "Python ETL alt süreci başlatılamadı.", null);

                    // 3 dakikalık bekleme sınırı koyuyoruz
                    using (var cts = new CancellationTokenSource(TimeSpan.FromMinutes(3)))
                    {
                        try
                        {
                            // Hem normal çıktıları hem de hataları asenkron okuyalım
                            string output = await process.StandardOutput.ReadToEndAsync(cts.Token);
                            string errors = await process.StandardError.ReadToEndAsync(cts.Token);
                            await process.WaitForExitAsync(cts.Token);

                            // VITAL ADIM: Python gizlice hata verdiyse bunu VS Code Terminaline basıyoruz!
                            Console.WriteLine($"\n=== PYTHON BİLGİ MESAJLARI ===\n{output}");
                            if (!string.IsNullOrWhiteSpace(errors))
                            {
                                Console.WriteLine($"\n=== PYTHON HATA MESAJLARI ===\n{errors}");
                            }

                            // Python 0 dışında bir kodla (örneğin 1) kapandıysa hata fırlat
                            if (process.ExitCode != 0)
                            {
                                return (false, $"Python işlemi başarısız oldu (Kod: {process.ExitCode}). Lütfen VS Code terminalindeki loglara bakın.", null);
                            }
                        }
                        catch (OperationCanceledException)
                        {
                            // 3 dakika dolduysa süreci zorla öldür
                            if (!process.HasExited)
                            {
                                process.Kill(); 
                            }
                            return (false, "İşlem 3 dakikayı aştığı için iptal edildi (Timeout).", null);
                        }
                    }
                }

                // 4. Veritabanı Doğrulaması
                var newProduct = await _productRepository.GetByUrlOrHashAsync(url, generatedHash);
                
                if (newProduct == null)
                    return (false, "Python işlemi hatasız tamamlandı ancak ürün veritabanında doğrulanamadı.", null);

                return (true, "Ürün yorumları başarıyla kazındı ve BERTurk modeli ile puanlandı!", newProduct.Id);
            }
            catch (Exception ex)
            {
                return (false, $"Arka plan süreci yürütülürken sistem hatası: {ex.Message}", null);
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
}