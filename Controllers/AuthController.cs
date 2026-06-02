using Microsoft.AspNetCore.Mvc;
using LLM_Destekli_Ozetleme.Models.DTOs;
using LLM_Destekli_Ozetleme.Services; 


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

        [HttpPost("register")]
        public async Task<IActionResult> Register([FromBody] RegisterDto request)
        {
            var result = await _authService.RegisterAsync(request);
            if (!result.Success) return BadRequest(result.Message);
            
            return Ok(new { message = result.Message });
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
    }
}