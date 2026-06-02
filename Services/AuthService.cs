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

        public async Task<AuthResult> RegisterAsync(RegisterDto registerDto)
        {
            if (await _context.Users.AnyAsync(u => u.Email == registerDto.Email))
                return new AuthResult { Success = false, Message = "Bu e-posta adresi zaten kullanılıyor." };

            if (await _context.Users.AnyAsync(u => u.Username == registerDto.Username))
                return new AuthResult { Success = false, Message = "Bu kullanıcı adı zaten alınmış." };

            string passwordHash = BCrypt.Net.BCrypt.HashPassword(registerDto.Password);

            var newUser = new User
            {
                Username = registerDto.Username,
                Email = registerDto.Email,
                PasswordHash = passwordHash,
                CreatedAt = DateTime.UtcNow
            };

            _context.Users.Add(newUser);
            await _context.SaveChangesAsync();

            return new AuthResult { Success = true, Message = "Kullanıcı başarıyla oluşturuldu!" };
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
        private string CreateAccessToken(User user)
        {
            var tokenHandler = new JwtSecurityTokenHandler();
            var key = Encoding.ASCII.GetBytes(_configuration["Jwt:Key"]); // appsettings.json'dan anahtarı alıyoruz 
            
            var tokenDescriptop = new SecurityTokenDescriptor
            {
                Subject = new ClaimsIdentity(new[]
                {
                    new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
                    new Claim(ClaimTypes.Name, user.Username),
                    new Claim(ClaimTypes.Email, user.Email)

                }),
                Expires = DateTime.UtcNow.AddMinutes(double.Parse(_configuration["Jwt:DurationInMinutes"] ?? "15")),
                Issuer = _configuration["Jwt:Issuer"],
                Audience = _configuration["Jwt:Audience"],
                SigningCredentials = new SigningCredentials(new SymmetricSecurityKey(key), SecurityAlgorithms.HmacSha256Signature)
            };

            var token = tokenHandler.CreateToken(tokenDescriptop);
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
            var tokenValidationParameters = new TokenValidationParameters
            {
                ValidateAudience = true,
                ValidateIssuer = true,
                ValidIssuer = _configuration["Jwt:Issuer"],
                ValidAudience = _configuration["Jwt:Audience"],
                ValidateIssuerSigningKey = true,
                IssuerSigningKey = new SymmetricSecurityKey(Encoding.ASCII.GetBytes(_configuration["Jwt:Key"])),
                ValidateLifetime = false
                
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
