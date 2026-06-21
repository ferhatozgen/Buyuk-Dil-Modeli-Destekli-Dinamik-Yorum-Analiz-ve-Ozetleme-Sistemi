namespace LLM_Destekli_Ozetleme.Models.DTOs
{
    public class TrendDataPointDto
    {
        public string PeriodLabel { get; set; } = string.Empty; // Uyarıyı çözer
        public DateTime StartDate { get; set; }
        public double AverageScore { get; set; }
        public int ReviewCount { get; set; }
    }

    public class ProductTrendDto
    {
        public Guid ProductId { get; set; }
        public string PeriodType { get; set; } = string.Empty; // Uyarıyı çözer
        public List<TrendDataPointDto> Trends { get; set; } = new List<TrendDataPointDto>();
    }
}