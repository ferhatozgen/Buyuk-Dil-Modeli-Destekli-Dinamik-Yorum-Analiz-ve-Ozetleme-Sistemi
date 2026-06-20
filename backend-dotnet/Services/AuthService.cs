using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using LLM_Destekli_Ozetleme.Data;
using LLM_Destekli_Ozetleme.Models.Entities;
using LLM_Destekli_Ozetleme.Models.DTOs;

namespace LLM_Destekli_Ozetleme.Services
{
    public class AuthService : IAuthService
    {
        private readonly AppDbContext _context;
        private readonly IConfiguration _configuration;

        public AuthService(AppDbContext context, IConfiguration configuration)
        {
            _context = context;
            _configuration = configuration;
        }

    
        public async Task<AuthResult> LoginAsync(LoginDto loginDto)
        {
            var user = await _context.Users.FirstOrDefaultAsync(u => u.Email == loginDto.Email);
            if (user == null || !BCrypt.Net.BCrypt.Verify(loginDto.Password, user.PasswordHash))
                return new AuthResult { Success = false, Message = "Geçersiz e-posta veya şifre." };

            var accessToken = CreateAccessToken(user);
            var refreshToken = GenerateRefreshToken();

            user.RefreshToken = refreshToken;
            user.RefreshTokenExpiryTime = DateTime.UtcNow.AddDays(7);
            _context.Users.Update(user);
            await _context.SaveChangesAsync();

            return new AuthResult
            {
                Success = true,
                Message = "Giriş başarılı.",
                AccessToken = accessToken,
                RefreshToken = refreshToken,
                Username = user.Username
            };
        }

        public async Task<AuthResult> RefreshTokenAsync(TokenDto tokenDto)
        {
                var principal = GetPrincipalFromExpiredToken(tokenDto.AccessToken);
                if (principal == null)
                    return new AuthResult { Success = false, Message = "Geçersiz erişim token'ı." };

                string username = principal.Identity?.Name ?? string.Empty;
            var user = await _context.Users.FirstOrDefaultAsync(u => u.Username == username);

            if (user == null || user.RefreshToken != tokenDto.RefreshToken || user.RefreshTokenExpiryTime <= DateTime.UtcNow)
                return new AuthResult { Success = false, Message = "Geçersiz refresh token veya token süresi dolmuş. Lütfen tekrar giriş yapın." };

            var newAccessToken = CreateAccessToken(user);
            var newRefreshToken = GenerateRefreshToken();

            user.RefreshToken = newRefreshToken;
            _context.Users.Update(user);
            await _context.SaveChangesAsync();

            return new AuthResult 
            { 
                Success = true, 
                AccessToken = newAccessToken, 
                RefreshToken = newRefreshToken 
            };
        }
        public async Task<AuthResult> LogoutAsync(Guid userId)
        {
            var user = await _context.Users.FindAsync(userId);
            if (user == null)
            {
                return new AuthResult { Success = false, Message = "Kullanıcı bulunamadı." };
            }

            user.RefreshToken = null;
            user.RefreshTokenExpiryTime = null;
            _context.Users.Update(user);
            await _context.SaveChangesAsync();

            return new AuthResult { Success = true, Message = "Çıkış başarılı." };
        }

        public async Task<UserProfileDto?> GetUserProfileAsync(Guid userId)
        {
            var user = await _context.Users.FindAsync(userId);
            if (user == null) return null;
            
            return new UserProfileDto
            {
                Id = user.Id,
                Username = user.Username ?? string.Empty,
                Email = user.Email ?? string.Empty
            };
        }
        private string CreateAccessToken(User user)
        {
            var tokenHandler = new JwtSecurityTokenHandler();
            
            // ÇÖZÜM: Eğer Jwt:Key boşsa doğrudan açıklayıcı bir hata fırlatıyoruz, böylece derleyici null ihtimalini eliyor.
            var jwtKey = _configuration["Jwt:Key"] ?? throw new InvalidOperationException("JWT Gizli Anahtarı (Jwt:Key) appsettings.json içinde bulunamadı!");
            var key = Encoding.ASCII.GetBytes(jwtKey); 
            
            var tokenDescriptor = new SecurityTokenDescriptor
            {
                Subject = new ClaimsIdentity(new[]
                {
                    new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
                    new Claim(ClaimTypes.Name, user.Username ?? string.Empty), // Kullanıcı adı null ihtimaline karşı koruma
                    new Claim(ClaimTypes.Email, user.Email ?? string.Empty)    // E-posta null ihtimaline karşı koruma
                }),
                Expires = DateTime.UtcNow.AddMinutes(double.Parse(_configuration["Jwt:DurationInMinutes"] ?? "15")),
                
                // ÇÖZÜM: Nullable alanlar için fallback olarak string.Empty atıyoruz
                Issuer = _configuration["Jwt:Issuer"] ?? string.Empty,
                Audience = _configuration["Jwt:Audience"] ?? string.Empty,
                SigningCredentials = new SigningCredentials(new SymmetricSecurityKey(key), SecurityAlgorithms.HmacSha256Signature)
            };

            var token = tokenHandler.CreateToken(tokenDescriptor);
            return tokenHandler.WriteToken(token);
        }

        private string GenerateRefreshToken()
        {
            var randomNumber = new byte[64];
            using var rng = RandomNumberGenerator.Create();
            rng.GetBytes(randomNumber);
            return Convert.ToBase64String(randomNumber);
        }

        private ClaimsPrincipal? GetPrincipalFromExpiredToken(string token)
        {
            // ÇÖZÜM: 139. satırdaki el sıkışma anahtarı için de null kontrolü eklendi
            var jwtKey = _configuration["Jwt:Key"] ?? throw new InvalidOperationException("JWT Gizli Anahtarı (Jwt:Key) appsettings.json içinde bulunamadı!");

            var tokenValidationParameters = new TokenValidationParameters
            {
                ValidateAudience = true,
                ValidateIssuer = true,
                ValidIssuer = _configuration["Jwt:Issuer"] ?? string.Empty,
                ValidAudience = _configuration["Jwt:Audience"] ?? string.Empty,
                ValidateIssuerSigningKey = true,
                IssuerSigningKey = new SymmetricSecurityKey(Encoding.ASCII.GetBytes(jwtKey)),
                ValidateLifetime = false // Süresi dolmuş token'ları çözebilmek için burası false kalmalı
            };

            var tokenHandler = new JwtSecurityTokenHandler();
            var principal = tokenHandler.ValidateToken(token, tokenValidationParameters, out SecurityToken securityToken);

            if (securityToken is not JwtSecurityToken jwtSecurityToken || 
                !jwtSecurityToken.Header.Alg.Equals(SecurityAlgorithms.HmacSha256, StringComparison.InvariantCultureIgnoreCase))
                throw new SecurityTokenException("Geçersiz token algoritması.");

            return principal;
        }
    }
}
