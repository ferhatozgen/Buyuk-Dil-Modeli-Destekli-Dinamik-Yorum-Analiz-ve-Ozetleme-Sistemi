using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LLM_Destekli_Ozetleme.Models.Entities
{
    [Table("summary_source_reviews")]
    public class SummarySourceReview
    {
        [Key]
        [Column("id")]
        public Guid Id { get; set; }

        [Column("summary_id")]
        public Guid SummaryId { get; set; }

        // DİKKAT: Veritabanında int4 olduğu için int yapıyoruz!
        [Column("review_id")]
        public int ReviewId { get; set; } 

        // Mimarideki İlişkiler
        [ForeignKey("SummaryId")]
        public ProductSummaries? ProductSummaries { get; set; }

        [ForeignKey("ReviewId")]
        public Review? Review { get; set; }
    }
}