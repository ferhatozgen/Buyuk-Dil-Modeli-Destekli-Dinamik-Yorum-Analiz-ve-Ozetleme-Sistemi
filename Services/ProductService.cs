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

        // DbContext bitti, ambar görevlilerini (repositories) çağırıyoruz
        public ProductService(IProductRepository productRepository, IReviewRepository reviewRepository)
        {
            _productRepository = productRepository;
                _reviewRepository = reviewRepository;
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