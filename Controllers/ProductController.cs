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
        [HttpGet("all")]
        public async Task<IActionResult> GetAll([FromQuery] ProductQueryParameters queryParams)
        {
            Guid? userId = null;

            // JWT Token içinden User ID'yi güvenli bir şekilde alıyoruz
            var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
            
            if (!string.IsNullOrEmpty(userIdClaim) && Guid.TryParse(userIdClaim, out Guid parsedUserId))
            {
                userId = parsedUserId;
            }

            // Çekilen ID'yi servise fırlatıyoruz
            var products = await _productService.GetProductsAsync(queryParams, userId);
            
            return Ok(products);
        }
        [AllowAnonymous] 
        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(Guid id)
        {
            if (id == Guid.Empty)
            {
                return BadRequest(new { message = "Geçersiz ürün ID." });
            }

            Guid? userId = null;
            
            // Eğer kullanıcı giriş yapmışsa (Header'da Bearer token varsa) ID'sini çıkarıyoruz
            var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
            
            if (!string.IsNullOrEmpty(userIdClaim) && Guid.TryParse(userIdClaim, out Guid parsedId))
            {
                userId = parsedId;
            }

            // Servise hem ürün ID'sini hem de varsa Kullanıcı ID'sini gönderiyoruz
            var productDetail = await _productService.GetProductDetailsByIdAsync(id, userId);

            if (productDetail == null)
            {
                return NotFound(new { message = "Ürün bulunamadı." });
            }

            return Ok(productDetail);
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

        [Authorize] 
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

        [Authorize] // 🌟 Sadece giriş yapmış kullanıcılar kendi koleksiyonunu görebilir
        [HttpGet("my-favorites")]
        public async Task<IActionResult> GetMyFavorites()
        {
            // JWT Token içerisinden isteği atan kullanıcının ID'sini cımbızlıyoruz
            var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;

            if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out Guid userId))
            {
                return Unauthorized(new { message = "Kullanıcı kimliği doğrulanamadı. Lütfen tekrar giriş yapın." });
            }

            // Kullanıcıya özel favori listesini getirip fırlatıyoruz
            var favoriteProducts = await _productService.GetFavoriteProductsAsync(userId);
            
            return Ok(favoriteProducts);
        }

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