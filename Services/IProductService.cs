using LLM_Destekli_Ozetleme.Models.Entities;
using LLM_Destekli_Ozetleme.Models.DTOs;

namespace LLM_Destekli_Ozetleme.Services
{
    public interface IProductService
    {
        Task<(bool Exists, string Message, Product? Product)> CheckUrlAsync(string url);
        Task<(bool Success, string Message, int Count, object? Reviews)> GetReviewsForModelAsync(Guid productId);
        Task<(bool NeedsRescrape, double MonthsPassed, string Message)> CheckProductStatusAsync(Guid productId);
        Task<List<ProductDisplayDto>> GetPopularProductsAsync(int minClicks);
        
        Task<(bool Success, string Message, Guid? ProductId)> ScrapeAndPredictAsync(string url);
    }
}