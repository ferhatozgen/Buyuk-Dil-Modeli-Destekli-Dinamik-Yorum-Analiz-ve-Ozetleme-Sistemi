using LLM_Destekli_Ozetleme.Models.Entities;

namespace LLM_Destekli_Ozetleme.Repositories
{
    public interface IReviewRepository
    {
        Task<List<Review>> GetCleanReviewsByProductIdAsync(Guid productId);
        IQueryable<Review> GetQueryable();
    }
}