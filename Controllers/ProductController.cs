using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using LLM_Destekli_Ozetleme.Models.DTOs;
using LLM_Destekli_Ozetleme.Services;

namespace LLM_Destekli_Ozetleme.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class ProductController : ControllerBase
    {
        private readonly IProductService _productService;

        // Artık veritabanı (AppDbContext) yerine doğrudan iş servisini enjekte ediyoruz
        public ProductController(IProductService productService)
        {
            _productService = productService;
        }

        [Authorize]
        [HttpPost("check-url")]
        public async Task<IActionResult> CheckUrl([FromBody] CheckProductUrlDto request)
        {
            if (string.IsNullOrEmpty(request.Url))
                return BadRequest("URL boş olamaz.");

            var result = await _productService.CheckUrlAsync(request.Url);

            return Ok(new 
            { 
                exists = result.Exists, 
                message = result.Message, 
                product = result.Product 
            });
        }

        [Authorize]
        [HttpGet("{productId}/reviews-for-model")]
        public async Task<IActionResult> GetReviewsForModel(Guid productId)
        {
            var result = await _productService.GetReviewsForModelAsync(productId);
            
            if (!result.Success)
                return NotFound(new { message = result.Message });

            return Ok(new 
            { 
                count = result.Count, 
                reviews = result.Reviews 
            });
        }

        [Authorize]
        [HttpGet("status/{productId}")]
        public async Task<IActionResult> CheckProductStatus(Guid productId)
        {
            try
            {
                var result = await _productService.CheckProductStatusAsync(productId);
                return Ok(new 
                { 
                    productId = productId,
                    monthsPassed = result.MonthsPassed,
                    needsRescrape = result.NeedsRescrape,
                    message = result.Message 
                });
            }
            catch (Exception ex)
            {
                return NotFound(new { message = ex.Message });
            }
        }

        [Authorize]
        [HttpGet("popular")]
        public async Task<IActionResult> GetPopularProducts([FromQuery] int minClicks = 50)
        {
            var popularProducts = await _productService.GetPopularProductsAsync(minClicks);

            if (!popularProducts.Any())
            {
                return Ok(new { message = "Şu anda popülerlik sınırını aşan ürün bulunmuyor.", products = popularProducts });
            }

            return Ok(popularProducts);
        }
        [Authorize]
        [HttpGet]
        public async Task<IActionResult> GetAll([FromQuery] ProductQueryParameters queryParams)
        {
            var products = await _productService.GetProductsAsync(queryParams);
            return Ok(products);

        }

        [HttpPost("step1-scrape")]
        public async Task<IActionResult> Step1Scrape([FromBody] CheckProductUrlDto request)
        {
           if (string.IsNullOrWhiteSpace(request.Url))
            {
                return BadRequest("Geçerli bir ürün URL'i girilmelidir.");
            }

            var result = await _productService.Step1ScrapeAsync(request.Url);

            if (!result.Success)
            {
                return StatusCode(500, new { message = result.Message });
            }

            return Ok(new 
            { 
                message = result.Message,
                productId = result.ProductId
            });
        }

        [HttpPost("step2-score")]
        public async Task<IActionResult> Step2Score([FromBody] ProductIdDto request)
        {
            if (request.ProductId == Guid.Empty)
            {
                return BadRequest("Geçerli bir ProductId girilmelidir.");
            }

            var result = await _productService.Step2ProcessAsync(request.ProductId);

            if (!result.Success)
            {
                return StatusCode(500, new { message = result.Message });
            }

            return Ok(new { message = result.Message });
        }

        [HttpPost("step3-categorize")]
        public async Task<IActionResult> Step3Categorize([FromBody] ProductIdDto request)
        {
            if (request.ProductId == Guid.Empty)
            {
                return BadRequest("Geçerli bir ürün ID'si girilmelidir.");
            }

            var result = await _productService.Step3CategorizeAsync(request.ProductId);

            if (!result.Success)
            {
                return StatusCode(500, new { message = result.Message });
            }

            return Ok(new { message = result.Message });
        }

        [HttpPost("step4-summarize")]
        public async Task<IActionResult> Step4Summarize([FromBody] ProductIdDto request)
        {
            if (request.ProductId == Guid.Empty)
            {
                return BadRequest("Geçerli bir ürün ID'si girilmelidir.");
            }

            var result = await _productService.Step4SummarizeAsync(request.ProductId);

            if (!result.Success)
            {
                return StatusCode(500, new { message = result.Message });
            }

            // Başarılı olduğunda React'e özet metnini de (summaryText) gönderiyoruz
            return Ok(new 
            { 
                message = result.Message,
                summaryText = result.Summary 
            });
        }

        [HttpPatch("{id}/click")]
        public async Task<IActionResult> IncrementClickCount(Guid id)
        {
            var result = await _productService.IncrementClickCountAsync(id);

            if (!result.Success)
            {
                return NotFound(new { message = result.Message });
            }

            return Ok(new { message = result.Message });
        }

        [Authorize] // 🌟 Bu endpoint'e sadece giriş yapmış ve geçerli Token'ı olanlar girebilir
        [HttpPost("{id}/toggle-save")]
        public async Task<IActionResult> ToggleSave(Guid id)
        {
            // JWT Token'ın içinden kullanıcının ID'sini (NameIdentifier) çıkarıyoruz
            var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;

            if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out Guid userId))
            {
                return Unauthorized(new { message = "Kullanıcı kimliği doğrulanamadı. Lütfen tekrar giriş yapın." });
            }

            // Servise gönder
            var result = await _productService.ToggleProductSaveAsync(userId, id);

            if (!result.Success)
            {
                return BadRequest(new { message = result.Message });
            }

            // Geriye işlemin başarılı olduğunu ve butonun yeni rengi için isSaved durumunu dönüyoruz
            return Ok(new { message = result.Message, isSaved = result.IsSaved });
        }

        // Parametre olarak body'den SummaryRatingRequestDto nesnesini alıyoruz

        [Authorize]
        [HttpPost("{id}/rate-summary")]
        public async Task<IActionResult> RateSummary(Guid id, [FromBody] SummaryRatingRequestDto request)
        {
            // Token'dan User ID'yi çıkartıyoruz
            var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;

            if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out Guid userId))
            {
                return Unauthorized(new { message = "Kullanıcı kimliği doğrulanamadı. Lütfen tekrar giriş yapın." });
            }

            // Servise gönderiyoruz
            var result = await _productService.RateSummaryAsync(userId, id, request.Rating);

            if (!result.Success)
            {
                return BadRequest(new { message = result.Message });
            }

            return Ok(new { message = result.Message });
        }
    }
}