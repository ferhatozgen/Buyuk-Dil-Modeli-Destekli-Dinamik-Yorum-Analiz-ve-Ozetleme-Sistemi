using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LLM_Destekli_Ozetleme.Models.Entities
{
    [Table("reviews")]
    public class Review
    {
        [Key]
        [Column("id")]
        public int Id { get; set; } // serial4 olduğu için int kullandık

        [Column("product_id")]
        public Guid? ProductId { get; set; }

        [Column("original_rating")]
        public decimal? OriginalRating { get; set; }

        [Column("predicted_score")]
        public decimal? PredictedScore { get; set; }

        [Column("raw_text")]
        public string? RawText { get; set; }

        [Column("clean_text")]
        public string? CleanText { get; set; }

        [Column("metadata")]
        public string? Metadata { get; set; } // jsonb alanını string olarak alıyoruz

        [Column("created_at")]
        public DateTime? CreatedAt { get; set; }

        [Column("rating_int")]
        public int? RatingInt { get; set; }

        [Column("is_summarized")]
        public bool? IsSummarized { get; set; }
        [Column("reviewed_at")]
        public DateTime? ReviewedAt { get; set; }
    }
}