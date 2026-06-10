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
                .AsNoTracking()
                .FirstOrDefaultAsync(p => p.UrlHash == hash || p.OriginalUrl == url);
        }

        public async Task<Product?> GetByIdAsync(Guid id)
        {
            // 🌟 FindAsync yerine AsNoTracking destekleyen bu yapı okuma hızını artırır
            return await _context.Products
                .AsNoTracking()
                .FirstOrDefaultAsync(p => p.Id == id);
        }

        public async Task<List<Product>> GetProductsAsync(ProductQueryParameters queryParams)
        {
            var query = _context.Products.AsNoTracking().AsQueryable();

            // Kategori Filtresi
            if (!string.IsNullOrWhiteSpace(queryParams.Category))
            {
                query = query.Where(p => p.Category != null && p.Category.ToLower() == queryParams.Category.ToLower());
            }

            // Arama Terimi Filtresi
            if (!string.IsNullOrEmpty(queryParams.SearchTerm))
            {
                query = query.Where(p => p.ProductName.Contains(queryParams.SearchTerm));
            }

            // Dinamik Sıralama Mantığı
            query = queryParams.SortBy switch
            {
                "mostClicked" => query.OrderByDescending(p => p.ClickCount),
                "mostLiked" => query.OrderByDescending(p => p.AvgModelScore),
                "mostControversial" => query.OrderByDescending(p => p.CeliskiScore),
                _ => query.OrderByDescending(p => p.CreatedAt)
            };

            // Sayfalama (Pagination) Mantığı
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
                .AsNoTracking()
                .Include(p => p.CategoryStats)
                .Include(p => p.SummaryHistories.OrderByDescending(sh => sh.Id).Take(1))
                .FirstOrDefaultAsync(p => p.Id == productId);
        }

        public async Task<List<Review>> GetReviewsByIdsAsync(List<int> reviewIds)
        {
            return await _context.Reviews
                .AsNoTracking()
                .Where(r => reviewIds.Contains(r.Id))
                .ToListAsync();
        }

        public async Task<List<Product>> GetFavoriteProductsAsync(Guid userId)
        {
            // 1. Önce sadece kaydedilmiş ürünlerin ID listesini bellek dostu bir şekilde çekiyoruz
            var favoriteProductIds = await _context.UserProductInteractions
                .AsNoTracking()
                .Where(i => i.UserId == userId && i.IsSaved && i.ProductId != null)
                .Select(i => i.ProductId!.Value)
                .ToListAsync();

            // 2. Ardından tek sorguda Products tablosundan AsNoTracking kullanarak verileri uçuruyoruz
            return await _context.Products
                .AsNoTracking()
                .Where(p => favoriteProductIds.Contains(p.Id))
                .ToListAsync();
        }

        public async Task<bool> IsProductFavoritedByUserAsync(Guid productId, Guid userId)
        {
            // 🌟 OPTİMİZASYON: Tüm satırı çekmek yerine .AnyAsync() kullanarak 
            // DB'den sadece true/false cevabı bekliyoruz. Muazzam hafıza tasarrufu sağlar.
            return await _context.UserProductInteractions
                .AsNoTracking()
                .AnyAsync(i => i.ProductId == productId && i.UserId == userId && i.IsSaved);
        }

        public async Task<bool> IncrementClickCountAsync(Guid id)
        {
            // Tıklama sayısını artırırken veriyi güncelleyeceğimiz için burada AsNoTracking KULLANILMAZ (Doğru yapmışsın)
            var product = await _context.Products.FirstOrDefaultAsync(p => p.Id == id);
            if (product == null) return false;

            product.ClickCount = (product.ClickCount ?? 0) + 1;
            product.LastUpdatedAt = DateTime.UtcNow;

            return await _context.SaveChangesAsync() > 0;
        }

        public async Task<UserProductInteraction?> GetUserInteractionAsync(Guid userId, Guid productId)
        {
            return await _context.UserProductInteractions
                .FirstOrDefaultAsync(x => x.UserId == userId && x.ProductId == productId);
        }

        public async Task<bool> SaveUserInteractionAsync(UserProductInteraction interaction)
        {
            if (interaction.Id == 0) 
            {
                await _context.UserProductInteractions.AddAsync(interaction);
            }
            else
            {
                _context.UserProductInteractions.Update(interaction);
            }
            
            return await _context.SaveChangesAsync() > 0;
        }

        public async Task<HashSet<Guid>> GetUserFavoriteProductIdsAsync(Guid userId)
        {
            var favoriteIds = await _context.UserProductInteractions
                .AsNoTracking()
                .Where(i => i.UserId == userId && i.IsSaved && i.ProductId != null)
                .Select(i => i.ProductId.Value) 
                .ToListAsync();

            return favoriteIds.ToHashSet();
        }
    }
}