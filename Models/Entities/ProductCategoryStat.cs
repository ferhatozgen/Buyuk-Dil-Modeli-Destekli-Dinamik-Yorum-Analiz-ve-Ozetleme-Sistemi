using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LLM_Destekli_Ozetleme.Models.Entities
{
    [Table("product_category_stats")]
    public class ProductCategoryStat
    {
        [Key]
        [Column("id")]
        public int Id { get; set; }

        [Column("product_id")]
        public Guid? ProductId { get; set; }

        [Column("category_name")]
        public string? CategoryName { get; set; }

        [Column("category_model_avg_score", TypeName = "decimal(3,2)")]
        public decimal? CategoryModelAvgScore { get; set; }

        [Column("updated_at")]
        public DateTime? UpdatedAt { get; set; }

        [Column("category_summary")]
        public string? CategorySummary { get; set; }

        [Column("source_review_ids", TypeName = "jsonb")]
        public List<int> SourceReviewIds { get; set; } = new List<int>();

        public Product? Product { get; set; }
    }
}