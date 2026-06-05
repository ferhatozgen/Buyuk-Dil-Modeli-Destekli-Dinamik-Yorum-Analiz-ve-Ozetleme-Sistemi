using LLM_Destekli_Ozetleme.Data;
using LLM_Destekli_Ozetleme.Models.Entities;
using LLM_Destekli_Ozetleme.Models.DTOs;
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

        public async Task<List<Product>> GetProductsAsync(ProductQueryParameters queryParams)
        {
            var query = _context.Products.AsQueryable();
            // Kategori Filtresi (Null uyarısını kapatan ve güvenli filtreleme yapan hali)
            if (!string.IsNullOrWhiteSpace(queryParams.Category))
            {
                query = query.Where(p => p.Category != null && p.Category.ToLower() == queryParams.Category.ToLower());
            }

            if (!string.IsNullOrEmpty(queryParams.SearchTerm))
            {
                query = query.Where(p => p.ProductName.Contains(queryParams.SearchTerm));
            }

            query = queryParams.SortBy switch
            {
                "mostClicked" => query.OrderByDescending(p => p.ClickCount),
                "mostLiked" => query.OrderByDescending(p => p.AvgModelScore),
                _ => query.OrderByDescending(p => p.CreatedAt)
            };

            if (queryParams.Limit.HasValue)
            {
                query = query.Take(queryParams.Limit.Value);
            }
            else
            {
                query = query.Skip((queryParams.PageNumber - 1) * queryParams.PageSize)
                             .Take(queryParams.PageSize);
            }

            return await query.ToListAsync();
        }

        public async Task<Product?> GetProductWithDetailsAsync(Guid productId)
        {
            return await _context.Products
                .Include(p => p.CategoryStats)
                .Include(p => p.SummaryHistories.OrderByDescending(sh => sh.Id).Take(1))
                .FirstOrDefaultAsync(p => p.Id == productId);
        }
        public async Task<List<Review>> GetReviewsByIdsAsync(List<int> reviewIds)
        {
            return await _context.Reviews
                .Where(r => reviewIds.Contains(r.Id))
                .ToListAsync();
        }
        public async Task<bool> IsProductFavoritedByUserAsync(Guid productId, Guid userId)
        {
            var interaction = await _context.UserProductInteractions
                .FirstOrDefaultAsync(i => i.ProductId == productId && i.UserId == userId);
            
            return interaction?.IsSaved ?? false;
        }
    }
}