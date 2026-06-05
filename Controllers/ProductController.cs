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
    }
}