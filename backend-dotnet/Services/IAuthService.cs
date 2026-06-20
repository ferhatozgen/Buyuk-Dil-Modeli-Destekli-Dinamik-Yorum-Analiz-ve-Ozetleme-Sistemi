using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

using LLM_Destekli_Ozetleme.Models.DTOs;

namespace LLM_Destekli_Ozetleme.Services
{
    public interface IAuthService
    {
        Task<AuthResult> RegisterAsync(RegisterDto registerDto);
        Task<AuthResult> LoginAsync(LoginDto loginDto);
        Task<AuthResult> RefreshTokenAsync(TokenDto tokenDto);
        Task<AuthResult> LogoutAsync(Guid userId);

        Task<UserProfileDto?> GetUserProfileAsync(Guid userId);
    }
}
