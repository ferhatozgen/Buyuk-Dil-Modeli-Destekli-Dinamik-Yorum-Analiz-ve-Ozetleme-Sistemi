using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using LLM_Destekli_Ozetleme.Data;
using LLM_Destekli_Ozetleme.Models.DTOs;
using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Authorization;

namespace LLM_Destekli_Ozetleme.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class ProductController : ControllerBase
    {
        private readonly AppDbContext _context;

        public ProductController(AppDbContext context)
        {
            _context = context;
        }

        // ENDPOINT 1: Link daha önce işlenmiş mi kontrolü
        [Authorize]
        [HttpPost("check-url")]
        public async Task<IActionResult> CheckUrl([FromBody] CheckProductUrlDto request)
        {
            if (string.IsNullOrEmpty(request.Url))
                return BadRequest("URL boş olamaz.");

            // Gelen URL'in Hash'ini alıyoruz (Veritabanındaki url_hash ile karşılaştırmak için)
            string generatedHash = GenerateSHA256Hash(request.Url);

            // Veritabanında Hash veya birebir orijinal URL ile arama yapıyoruz
            var existingProduct = await _context.Products
                .FirstOrDefaultAsync(p => p.UrlHash == generatedHash || p.OriginalUrl == request.Url);

            if (existingProduct != null)
            {
                // Ürün bulundu! Frontend'e "tekrar scrape yapma, veriyi al ve göster" diyoruz.
                return Ok(new 
                { 
                    exists = true, 
                    message = "Ürün veritabanında mevcut.", 
                    product = existingProduct 
                });
            }

            // Ürün yok, frontend'e "bu yeni bir ürün, scrape başlatılmalı" mesajı dönüyoruz
            return Ok(new 
            { 
                exists = false, 
                message = "Ürün bulunamadı, yeni analiz başlatılmalı." 
            });
        }

        // ENDPOINT 2: Model için Yorumları Getirme
        [Authorize]
        [HttpGet("{productId}/reviews-for-model")]
        public async Task<IActionResult> GetReviewsForModel(Guid productId)
        {
            // Veritabanındaki "product_id" ile eşleşen yorumları buluyoruz.
            // Sadece Llama modelinin işine yarayacak "temiz metin" (CleanText) kısımlarını seçiyoruz ki veri yükü hafiflesin.
            var reviews = await _context.Reviews
                .Where(r => r.ProductId == productId && !string.IsNullOrEmpty(r.CleanText))
                .Select(r => new 
                {
                    r.Id,
                    r.CleanText,
                    r.OriginalRating
                })
                .ToListAsync();

            if (!reviews.Any())
                return NotFound(new { message = "Bu ürüne ait yorum bulunamadı veya henüz scrape edilmedi." });

            return Ok(new 
            { 
                count = reviews.Count, 
                reviews = reviews 
            });
        }

        [Authorize]
        [HttpGet("status/{productId}")]
        public async Task<IActionResult> CheckProductStatus(Guid productId)
        {
            var product = await _context.Products.FindAsync(productId);
            
            if (product == null)
                return NotFound(new { message = "Ürün bulunamadı." });

            // Ürünün veritabanına eklenme (veya güncellenme) tarihini alıyoruz
            // Kullanıcı 'created_at' dediği için onu baz alıyoruz, null ise şu anı sayıyoruz.
            var referenceDate = product.CreatedAt ?? DateTime.UtcNow;
            
            // Tarih farkını ay cinsinden hesaplama
            var monthsPassed = (DateTime.UtcNow - referenceDate).TotalDays / 30.0;
            
            // Eğer 3 aydan (yaklaşık 90 gün) fazla zaman geçmişse yeniden scrape edilmeli
            bool needsRescrape = monthsPassed > 3.0;

            return Ok(new 
            { 
                productId = product.Id,
                monthsPassed = Math.Round(monthsPassed, 1),
                needsRescrape = needsRescrape,
                message = needsRescrape 
                    ? "Ürün verileri 3 aydan eski. Yeniden scrape işlemi başlatılmalı." 
                    : "Ürün verileri güncel. Tekrar scrape edilmesine gerek yok."
            });
        }

        // ENDPOINT 4: Popüler (En Çok Tıklanan) Ürünleri Getirme
        [Authorize]
        [HttpGet("popular")]
        public async Task<IActionResult> GetPopularProducts([FromQuery] int minClicks = 50)
        {
            // click_count değeri minClicks'ten (varsayılan 50) büyük olanları getirir, 
            // en çok tıklanandan aza doğru sıralar ve oluşturduğumuz DTO formatına çevirir.
            var popularProducts = await _context.Products
                .Where(p => p.ClickCount != null && p.ClickCount >= minClicks)
                .OrderByDescending(p => p.ClickCount)
                .Take(20) // Arayüzü yormamak için ilk 20 popüler ürünü alıyoruz
                .Select(p => new ProductDisplayDto
                {
                    ProductName = p.ProductName,
                    Category = p.Category,
                    AvgOrjScore = p.AvgOrjScore,
                    AvgModelScore = p.AvgModelScore,
                    GuncelOzet = p.GuncelOzet
                })
                .ToListAsync();

            if (!popularProducts.Any())
            {
                return Ok(new { message = "Şu anda popülerlik sınırını aşan ürün bulunmuyor.", products = popularProducts });
            }

            return Ok(popularProducts);
        }

        // YARDIMCI FONKSİYON: Python'daki hashlib mantığının C# karşılığı
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