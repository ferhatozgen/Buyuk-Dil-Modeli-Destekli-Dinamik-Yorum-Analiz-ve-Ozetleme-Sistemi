using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace LLM_Destekli_Ozetleme.Models.DTOs
{
    public class ProductQueryParameters
    {
        public int PageNumber { get; set; } = 1;
        public int PageSize { get; set; } = 10;
        public string? SortBy { get; set; }
        public string? Category { get; set; }
        public string? SearchTerm { get; set; }
        public int? Limit { get; set; }
    }
}