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

        [Column("category_model_avg_score")]
        public decimal? CategoryModelAvgScore { get; set; }

        [Column("product_model_avg_score")]
        public decimal? ProductModelAvgScore { get; set; }

        [Column("updated_at")]
        public DateTime? UpdatedAt { get; set; }
    }
}