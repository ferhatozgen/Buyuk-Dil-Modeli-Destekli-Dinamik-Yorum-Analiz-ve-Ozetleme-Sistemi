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
        public DbSet<ProductSummaries> ProductSummaries { get; set; }
        public DbSet<ReviewAspect> ReviewAspects { get; set; }
        public DbSet<SummarySourceReview> SummarySourceReviews { get; set; }
        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            modelBuilder.Entity<ProductSummaries>().ToTable("product_summaries");
            modelBuilder.Entity<ReviewAspect>().ToTable("review_aspects");
            modelBuilder.Entity<SummarySourceReview>().ToTable("summary_source_reviews");
            modelBuilder.Entity<Product>(entity =>
            {
                entity.HasMany(p => p.ProductSummaries)
                      .WithOne(s => s.Product)
                      .HasForeignKey(s => s.ProductId)
                      .OnDelete(DeleteBehavior.Cascade);

                entity.HasMany(p => p.Reviews)
                      .WithOne() 
                      .HasForeignKey(r => r.ProductId)
                      .OnDelete(DeleteBehavior.Cascade); // Ürün silinirse yorumları da silinir

                entity.Property(e => e.ClickCount)
                      .HasDefaultValue(0);
            });

        }
    }
}