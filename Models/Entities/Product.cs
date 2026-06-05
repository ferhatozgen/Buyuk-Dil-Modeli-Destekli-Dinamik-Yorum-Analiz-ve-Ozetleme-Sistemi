using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LLM_Destekli_Ozetleme.Models.Entities
{
    [Table("products")]
    public class Product
    {
        [Key]
        [Column("id")]
        public Guid Id { get; set; }

        [Column("platform")]
        public string Platform { get; set; } = string.Empty;

        [Column("platform_id")]
        public string PlatformId { get; set; } = string.Empty;

        [Column("product_name")]
        public string ProductName { get; set; } = string.Empty;

        [Column("image_url")]
        public string? ImageUrl { get; set; }

        [Column("category")]
        public string? Category { get; set; }

        [Column("original_url")]
        public string OriginalUrl { get; set; } = string.Empty;

        [Column("url_hash")]
        public string? UrlHash { get; set; }

        [Column("status")]
        public string? Status { get; set; }

        [Column("click_count")]
        public int? ClickCount { get; set; }

        [Column("avg_orj_score")]
        public decimal? AvgOrjScore { get; set; }

        [Column("avg_model_score")]
        public decimal? AvgModelScore { get; set; }

        [Column("guncel_ozet")]
        public string? GuncelOzet { get; set; }

        [Column("created_at")]
        public DateTime? CreatedAt { get; set; }

        [Column("last_updated_at")]
        public DateTime? LastUpdatedAt { get; set; }

        [Column("celiski_score")]
        public decimal CeliskiScore { get; set; } = 0.00m;
    }
}