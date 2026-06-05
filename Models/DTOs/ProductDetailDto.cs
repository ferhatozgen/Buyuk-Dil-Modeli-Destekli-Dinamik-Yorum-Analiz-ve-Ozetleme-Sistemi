using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace LLM_Destekli_Ozetleme.Models.DTOs
{
    public class ProductDetailDto
    {
        public Guid Id { get; set; }
        public string ProductName { get; set; } = string.Empty;
        public string Platform { get; set; } = string.Empty;

        public string? Category { get; set; }
        public string? ImageUrl { get; set; }
        public string OriginalUrl { get; set; } = string.Empty;
        public decimal? AvgOrjScore { get; set; }
        public decimal? AvgModelScore { get; set; }
        public decimal? CeliskiScore { get; set; }

        public string? GuncelOzet { get; set; }
        public List<CategoricalStatDto> CategoricalStats { get; set; } = new();
        public List<SourceReviewDto> SourceReviews { get; set; } = new();

        public bool IsFavorited { get; set; }
    }

    public class CategoricalStatDto
    {
        public string? CategoryName { get; set; } = string.Empty;
        public decimal? CategoryModelAvgScore { get; set; }
        public string? CategorySummary { get; set; }
    }

    public class SourceReviewDto
    {
        public string Text { get; set; } = string.Empty;
    }
}