using Microsoft.EntityFrameworkCore;
using LLM_Destekli_Ozetleme.Models.Entities;

namespace LLM_Destekli_Ozetleme.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

        public DbSet<User> Users { get; set; }
        public DbSet<Product> Products { get; set; }
        public DbSet<Review> Reviews { get; set; }
        
        // Dikkat: Burada artık alt tire yok, yeni sınıf isimlerimizi kullanıyoruz!
        public DbSet<UserProductInteraction> UserProductInteractions { get; set; }
        public DbSet<ProductSummaryHistory> ProductSummaryHistories { get; set; }
        public DbSet<ProductCategoryStat> ProductCategoryStats { get; set; }
    }
}