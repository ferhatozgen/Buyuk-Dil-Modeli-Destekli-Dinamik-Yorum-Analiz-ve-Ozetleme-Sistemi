using LLM_Destekli_Ozetleme.Models.Entities;
using LLM_Destekli_Ozetleme.Models.DTOs;

namespace LLM_Destekli_Ozetleme.Repositories
{
    public interface IProductRepository
    {
        Task<Product?> GetByUrlOrHashAsync(string url, string hash);
        Task<Product?> GetByIdAsync(Guid id);
        Task<List<Product>> GetPopularProductsAsync(int minClicks, int limit);
        Task<List<Product>> GetProductsAsync(ProductQueryParameters queryParams);
        Task<bool> IncrementClickCountAsync(Guid id);
        Task<UserProductInteraction?> GetUserInteractionAsync(Guid userId, Guid productId);
        Task<bool> SaveUserInteractionAsync(UserProductInteraction interaction);
    }
}