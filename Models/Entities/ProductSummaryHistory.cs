using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LLM_Destekli_Ozetleme.Models.Entities
{
    [Table("product_summary_history")]
    public class ProductSummaryHistory
    {
        [Key]
        [Column("id")]
        public int Id { get; set; }

        [Column("product_id")]
        public Guid? ProductId { get; set; }

        [Column("old_summary")]
        public string? OldSummary { get; set; }

        [Column("old_price")]
        public decimal? OldPrice { get; set; }

        [Column("valid_from")]
        public DateTime? ValidFrom { get; set; }

        [Column("valid_until")]
        public DateTime? ValidUntil { get; set; }
    }
}