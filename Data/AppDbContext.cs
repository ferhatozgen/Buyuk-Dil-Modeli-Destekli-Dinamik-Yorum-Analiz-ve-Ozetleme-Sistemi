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

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            
            modelBuilder.Entity<Product>(entity =>
            {
                entity.HasMany(p => p.CategoryStats)
                      .WithOne(c => c.Product)
                      .HasForeignKey(c => c.ProductId)
                      .OnDelete(DeleteBehavior.Cascade); // Ürün silinirse kategorileri de silinir

                entity.HasMany(p => p.SummaryHistories)
                      .WithOne(s => s.Product)
                      .HasForeignKey(s => s.ProductId)
                      .OnDelete(DeleteBehavior.Cascade); // Ürün silinirse özet geçmişi de silinir

                entity.HasMany(p => p.Reviews)
                      .WithOne() 
                      .HasForeignKey(r => r.ProductId)
                      .OnDelete(DeleteBehavior.Cascade); // Ürün silinirse yorumları da silinir

                entity.Property(e => e.ClickCount)
                      .HasDefaultValue(0);
            });

            // --- ProductCategoryStat Konfigürasyonu (JSONB) ---
            modelBuilder.Entity<ProductCategoryStat>(entity =>
            {
                // JSONB dizisi için veritabanı seviyesinde boş liste ataması
                entity.Property(e => e.SourceReviewIds)
                      .HasDefaultValueSql("'[]'::jsonb");
            });

            // --- ProductSummaryHistory Konfigürasyonu (JSONB) ---
            modelBuilder.Entity<ProductSummaryHistory>(entity =>
            {
                // JSONB dizisi için veritabanı seviyesinde boş liste ataması
                entity.Property(e => e.SourceReviewIds)
                      .HasDefaultValueSql("'[]'::jsonb");
            });
        }
    }
}