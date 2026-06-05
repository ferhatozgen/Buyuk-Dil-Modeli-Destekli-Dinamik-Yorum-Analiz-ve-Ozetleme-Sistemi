using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace LLM_Destekli_Ozetleme.Models.DTOs
{
    public class ProductListDto
    {
        public Guid Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Category { get; set; } = string.Empty;
        public decimal? ModelScore { get; set; } // Yapay zekanın öngördüğü puan
        public int ClickCount { get; set; }
        public string? ImageUrl { get; set; } // Eğer veritabanında görsel alanı varsa
        public string? PlatformName { get; set; }
        public bool IsFavorited { get; set; }
    }
}