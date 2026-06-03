using LLM_Destekli_Ozetleme.Models.Entities;
using LLM_Destekli_Ozetleme.Models.DTOs;

namespace LLM_Destekli_Ozetleme.Services
{
    public interface IProductService
    {
        // Tuple kullanarak hem durum bilgisini hem de veriyi tek seferde dönüyoruz
        Task<(bool Exists, string Message, Product? Product)> CheckUrlAsync(string url);
        Task<(bool Success, string Message, int Count, object? Reviews)> GetReviewsForModelAsync(Guid productId);
        Task<(bool NeedsRescrape, double MonthsPassed, string Message)> CheckProductStatusAsync(Guid productId);
        Task<List<ProductDisplayDto>> GetPopularProductsAsync(int minClicks);
    }
}