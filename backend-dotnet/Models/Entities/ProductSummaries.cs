using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LLM_Destekli_Ozetleme.Models.Entities
{
    public class ProductSummaries
    {
        [Key]
        [Column("id")]
        public Guid Id { get; set; }

        [Column("product_id")]
        public Guid ProductId { get; set; }

        [Column("summary_type")]
        public string SummaryType { get; set; } = string.Empty; // "GENERAL" veya "CATEGORY"

        [Column("category_name")]
        public string? CategoryName { get; set; } // "GENERAL" tipindekiler için null gelecektir

        [Column("summary_text")]
        public string SummaryText { get; set; } = string.Empty;

        [Column("average_score")]
        public decimal? AvgScore { get; set; }

        [Column("created_at")]
        public DateTime? CreatedAt { get; set; }

        // Mimarideki Product ilişkisi (Ters Navigasyon)
        [ForeignKey("ProductId")]
        public Product? Product { get; set; }
    }
}