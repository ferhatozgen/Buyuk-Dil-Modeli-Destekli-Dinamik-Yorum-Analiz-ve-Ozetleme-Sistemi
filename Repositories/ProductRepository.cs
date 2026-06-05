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

        public async Task<List<Product>> GetPopularProductsAsync(int minClicks, int limit)
        {
            return await _context.Products
                .Where(p => p.ClickCount != null && p.ClickCount >= minClicks)
                .OrderByDescending(p => p.ClickCount)
                .Take(limit)
                .ToListAsync();
        }

        public async Task<List<Product>> GetProductsAsync(ProductQueryParameters queryParams)
        {
            var query = _context.Products.AsQueryable();

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
                // 🌟 YENİ SÜTUN İÇİN DİNAMİK SIRALAMA SEÇENEĞİ:
                // Çelişki skoru en yüksek olan (yani tahminle orijinal puanın en çok saptığı) ürünleri başa çeker.
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

        public async Task<bool> IncrementClickCountAsync(Guid id)
        {
            var product = await _context.Products.FindAsync(id);
            if (product == null) return false;

            // Eğer click_count null ise 1 yapıyoruz, değer varsa 1 arttırıyoruz.
            product.ClickCount = (product.ClickCount ?? 0) + 1;
            product.LastUpdatedAt = DateTime.UtcNow;

            return await _context.SaveChangesAsync() > 0;
        }

        public async Task<UserProductInteraction?> GetUserInteractionAsync(Guid userId, Guid productId)
        {
            // Kullanıcının bu ürünle daha önce bir kaydı var mı diye bakıyoruz
            return await _context.UserProductInteractions
                .FirstOrDefaultAsync(x => x.UserId == userId && x.ProductId == productId);
        }

        public async Task<bool> SaveUserInteractionAsync(UserProductInteraction interaction)
        {
            if (interaction.Id == 0) 
            {
                // Eğer Id 0 ise bu yepyeni bir kayıttır (Insert)
                await _context.UserProductInteractions.AddAsync(interaction);
            }
            else
            {
                // Kayıt varsa durumu güncelleniyordur (Update)
                _context.UserProductInteractions.Update(interaction);
            }
            
            return await _context.SaveChangesAsync() > 0;
        }
    }
}