// Services/IProductService.cs dosyasının içeriğini bunula değiştir:
using LLM_Destekli_Ozetleme.Models.DTOs;
using LLM_Destekli_Ozetleme.Models.Entities;

namespace LLM_Destekli_Ozetleme.Services
{
    public interface IProductService
    {
        // 🌟 userId parametresi buraya eklendi!
        Task<List<ProductListDto>> GetProductsAsync(ProductQueryParameters queryParams, Guid? userId = null);

        Task<ProductDetailDto?> GetProductDetailsByIdAsync(Guid productId, Guid? userId = null);
        Task<(bool Exists, string Message, Product? Product)> CheckUrlAsync(string url);
        Task<(bool NeedsRescrape, double MonthsPassed, string Message)> CheckProductStatusAsync(Guid productId);
        Task<(bool Success, string Message, int Count, object? Reviews)> GetReviewsForModelAsync(Guid productId);
        Task<(bool Success, string Message, Guid? ProductId)> Step1ScrapeAsync(string url);
        Task<(bool Success, string Message)> Step2ProcessAsync(Guid productId);
        Task<(bool Success, string Message)> Step3CategorizeAsync(Guid productId);
        Task<(bool Success, string Message, string? Summary)> Step4SummarizeAsync(Guid productId);
        Task<(bool Success, string Message)> IncrementClickCountAsync(Guid productId);
        Task<(bool Success, string Message, bool IsSaved)> ToggleProductSaveAsync(Guid userId, Guid productId);
        Task<(bool Success, string Message)> RateSummaryAsync(Guid userId, Guid productId, int rating);
    }
}