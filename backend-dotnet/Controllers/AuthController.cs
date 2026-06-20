using Microsoft.AspNetCore.Mvc;
using LLM_Destekli_Ozetleme.Models.DTOs;
using LLM_Destekli_Ozetleme.Services; 
using Microsoft.AspNetCore.Authorization;


namespace LLM_Destekli_Ozetleme.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly IAuthService _authService;

        // Artık DbContext'e değil, direkt yazdığımız servise bağlanıyoruz
        public AuthController(IAuthService authService)
        {
            _authService = authService;
        }


        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginDto request)
        {
            var result = await _authService.LoginAsync(request);
            if (!result.Success) return BadRequest(result.Message);

            return Ok(new 
            { 
                accessToken = result.AccessToken,
                refreshToken = result.RefreshToken,
                username = result.Username,
                message = result.Message 
            });
        }

        [HttpPost("refresh")]
        public async Task<IActionResult> Refresh([FromBody] TokenDto request)
        {
            if (request == null) return BadRequest("Geçersiz istek.");

            var result = await _authService.RefreshTokenAsync(request);
            if (!result.Success) return BadRequest(result.Message);

            return Ok(new 
            { 
                accessToken = result.AccessToken,
                refreshToken = result.RefreshToken
            });  
        }

        [Authorize]
        [HttpPost("logout")]
        public async Task<IActionResult> Logout()
        {
            var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier);
            if (userIdClaim == null)
            {
                return Unauthorized();
            }

            var result = await _authService.LogoutAsync(Guid.Parse(userIdClaim.Value));
            if (!result.Success) return BadRequest(result.Message);
            return Ok(new { message = result.Message });

        }
        [Authorize]
        [HttpGet("me")]
        public async Task<IActionResult> GetMe()
        {
            var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier);
            if (userIdClaim == null)
            {
                return Unauthorized();
            }

            var userProfile = await _authService.GetUserProfileAsync(Guid.Parse(userIdClaim.Value));
            if (userProfile == null) return NotFound("Kullanıcı bulunamadı.");

            return Ok(userProfile);
        }
    }
}