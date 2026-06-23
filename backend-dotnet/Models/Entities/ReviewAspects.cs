using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LLM_Destekli_Ozetleme.Models.Entities
{
    [Table("review_aspects")]
    public class ReviewAspect
    {
        [Key]
        [Column("id")]
        public Guid Id { get; set; }

        [Column("review_id")]
        public int ReviewId { get; set; }

        [Column("category_name")]
        public string CategoryName { get; set; } = string.Empty;

        [Column("snippet_text")]
        public string SnippetText { get; set; } = string.Empty;

        [Column("snippet_score")]
        public decimal? SnippetScore { get; set; }

        [Column("created_at")]
        public DateTime? CreatedAt { get; set; }

        // Mimarideki Review ilişkisi (Ters Navigasyon)
        [ForeignKey("ReviewId")]
        public Review? Review { get; set; }
    }
}