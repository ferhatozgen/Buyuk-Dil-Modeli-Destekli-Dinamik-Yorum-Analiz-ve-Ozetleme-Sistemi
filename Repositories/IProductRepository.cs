using LLM_Destekli_Ozetleme.Models.Entities;

namespace LLM_Destekli_Ozetleme.Repositories
{
    public interface IProductRepository
    {
        Task<Product?> GetByUrlOrHashAsync(string url, string hash);
        Task<Product?> GetByIdAsync(Guid id);
        Task<List<Product>> GetPopularProductsAsync(int minClicks, int limit);
    }
}