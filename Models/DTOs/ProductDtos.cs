namespace LLM_Destekli_Ozetleme.Models.DTOs
{
    public class CheckProductUrlDto
    {
        public string Url { get; set; } = string.Empty;
    }

    public class ProductDisplayDto
    {
        public string ProductName { get; set; } = string.Empty;
        public string? Category { get; set; }
        public decimal? AvgOrjScore { get; set; }
        public decimal? AvgModelScore { get; set; } 
        public string? GuncelOzet { get; set; }
    }
}