using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LLM_Destekli_Ozetleme.Models.Entities
{
    [Table("user_product_interactions")]
    public class UserProductInteraction
    {
        [Key]
        [Column("id")]
        public int Id { get; set; }

        [Column("user_id")]
        public Guid? UserId { get; set; }

        [Column("product_id")]
        public Guid? ProductId { get; set; }

        [Column("is_saved")]
        public bool IsSaved { get; set; }

        [Column("summary_rating")]
        public int? SummaryRating { get; set; }

        [Column("created_at")]
        public DateTime? CreatedAt { get; set; }
    }
}