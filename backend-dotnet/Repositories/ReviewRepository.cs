using LLM_Destekli_Ozetleme.Data;
using LLM_Destekli_Ozetleme.Models.Entities;
using Microsoft.EntityFrameworkCore;


namespace LLM_Destekli_Ozetleme.Repositories
{
    public class ReviewRepository : IReviewRepository
    {
        private readonly AppDbContext _context;

        public ReviewRepository(AppDbContext context)
        {
            _context = context;
        }

        public async Task<List<Review>> GetCleanReviewsByProductIdAsync(Guid productId)
        {
            return await _context.Reviews
                .Where(r => r.ProductId == productId && !string.IsNullOrEmpty(r.CleanText))
                .ToListAsync();
        }
        public IQueryable<Review> GetQueryable() => _context.Reviews.AsQueryable();
    }
}