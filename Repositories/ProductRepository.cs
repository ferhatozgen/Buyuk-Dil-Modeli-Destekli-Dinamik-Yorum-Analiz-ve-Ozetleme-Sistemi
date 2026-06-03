using LLM_Destekli_Ozetleme.Data;
using LLM_Destekli_Ozetleme.Models.Entities;
using Microsoft.EntityFrameworkCore;

namespace LLM_Destekli_Ozetleme.Repositories
{
    public class ProductRepository : IProductRepository
    {
        private readonly AppDbContext _context;

        public ProductRepository(AppDbContext context)
        {
            _context = context;
        }

        public async Task<Product?> GetByUrlOrHashAsync(string url, string hash)
        {
            return await _context.Products
                .FirstOrDefaultAsync(p => p.UrlHash == hash || p.OriginalUrl == url);
        }

        public async Task<Product?> GetByIdAsync(Guid id)
        {
            return await _context.Products.FindAsync(id);
        }

        public async Task<List<Product>> GetPopularProductsAsync(int minClicks, int limit)
        {
            return await _context.Products
                .Where(p => p.ClickCount != null && p.ClickCount >= minClicks)
                .OrderByDescending(p => p.ClickCount)
                .Take(limit)
                .ToListAsync();
        }
    }
}