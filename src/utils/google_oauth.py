import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urlparse as parse_url

from loguru import logger
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright, Error as PlaywrightError


@dataclass
class OAuthConfig:
    """Configuration for OAuth client"""
    cdp_url: str = "http://localhost:9222"
    headless: bool = False
    timeout: int = 30000
    retry_attempts: int = 3
    retry_delay: float = 1.0
    output_dir: Optional[Path] = None
    user_agent: Optional[str] = None
    viewport_size: Tuple[int, int] = (1920, 1080)


class GoogleOAuthError(Exception):
    """Custom exception for OAuth-related errors"""
    pass


class GoogleOAuthClient:
    """Optimized Google OAuth automation client with improved resource management"""
    
    def __init__(
        self,
        config: Optional[OAuthConfig] = None,
    ):
        # Support both new config object and legacy parameters
        if config:
            self.config = config
        else:
            self.config = OAuthConfig()
        
        if self.config.output_dir is None:
            self.config.output_dir = Path.cwd()
            
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        
        logger.info("GoogleOAuth client initialized")
        logger.debug(f"Config: {self.config}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.close()

    async def close(self):
        """Clean up resources"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.debug("Resources cleaned up")

    @asynccontextmanager
    async def _get_browser_context(self):
        """Get browser and context with proper resource management"""
        browser = None
        context = None
        try:
            browser = await self._get_or_create_browser()
            
            # Create context with optimized settings
            context_options = {
                "viewport": {"width": self.config.viewport_size[0], "height": self.config.viewport_size[1]},
                "ignore_https_errors": True,
                "java_script_enabled": True,
            }
            
            if self.config.user_agent:
                context_options["user_agent"] = self.config.user_agent
                
            context = await browser.new_context(**context_options)
            
            # Configure context for better performance
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            yield browser, context
            
        finally:
            if context:
                await context.close()

    async def _get_or_create_browser(self) -> Browser:
        """Get browser instance, either by connecting to CDP or launching new"""
        if self._browser and not self._browser.is_connected():
            self._browser = None
            
        if self._browser:
            return self._browser
            
        if not self._playwright:
            self._playwright = await async_playwright().__aenter__()
        
        try:
            # Try to connect to existing Chrome instance
            self._browser = await self._playwright.chromium.connect_over_cdp(self.config.cdp_url)
            logger.success("Connected to existing Chrome instance via CDP")
        except Exception as e:
            logger.warning(f"Failed to connect via CDP ({e}), launching new browser")
            launch_options = {
                "headless": self.config.headless,
                "args": [
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor"
                ]
            }
            self._browser = await self._playwright.chromium.launch(**launch_options)
            logger.success("Launched new browser instance")
            
        return self._browser

    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        last_exception = GoogleOAuthError("Operation failed")
        
        for attempt in range(self.config.retry_attempts):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.retry_attempts - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.warning(f"Operation failed (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                    logger.debug(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.config.retry_attempts} attempts")
        
        raise last_exception

    async def _find_google_oauth_button(self, page: Page) -> Optional[Any]:
        """Find Google OAuth button using multiple selectors with improved detection"""
        selectors = [
            'text="Sign in with Google"',
            'text="Continue with Google"',
            'text="Login with Google"',
            '[data-testid*="google" i]',
            '[data-provider="google" i]',
            'button:has-text("Google")',
            '[aria-label*="Google" i]',
            '.google-oauth-button',
            '[class*="google" i]:visible',
            'a[href*="google.com/oauth"]',
            'button[class*="google" i]'
        ]
        
        # Try selectors in parallel for better performance
        tasks = []
        for selector in selectors:
            task = asyncio.create_task(self._check_selector_visibility(page, selector))
            tasks.append((selector, task))
        
        for selector, task in tasks:
            try:
                element = await asyncio.wait_for(task, timeout=2.0)
                if element:
                    logger.success(f"Found Google OAuth button with selector: {selector}")
                    return element
            except (asyncio.TimeoutError, Exception):
                continue
        
        logger.error("Could not find Google OAuth button with any known selector")
        return None

    async def _check_selector_visibility(self, page: Page, selector: str) -> Optional[Any]:
        """Check if a selector is visible"""
        try:
            element = page.locator(selector)
            if await element.is_visible(timeout=1000):
                return element
        except Exception:
            pass
        return None

    async def _perform_google_login(self, page: Page, email: str, password: str) -> bool:
        """Perform Google login flow with improved error handling"""
        try:
            # Wait for Google login page
            await page.wait_for_url("**/accounts.google.com/**", timeout=self.config.timeout)
            logger.info("Reached Google login page")
            
            # Wait for and fill email
            email_selectors = ['input[type="email"]', '[id="identifierId"]', 'input[name="identifier"]']
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = page.locator(selector)
                    await email_input.wait_for(timeout=5000)
                    break
                except Exception:
                    continue
            
            if not email_input:
                raise GoogleOAuthError("Could not find email input field")
                
            await email_input.fill(email)
            await page.wait_for_timeout(1000)  # Small delay for form processing
            logger.debug("Email filled")
            
            # Click Next button
            next_selectors = ['button:has-text("Next")', '[id="identifierNext"]', 'input[type="submit"]', 'button[type="submit"]']
            next_clicked = False
            for selector in next_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    logger.debug(f"Clicked Next button with selector: {selector}")
                    next_clicked = True
                    break
                except Exception:
                    continue
            
            if not next_clicked:
                raise GoogleOAuthError("Could not find or click Next button")
            
            # Wait for password page
            password_selectors = ['input[type="password"]', '[name="password"]', '[id="password"]']
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = page.locator(selector)
                    await password_input.wait_for(timeout=self.config.timeout)
                    break
                except Exception:
                    continue
            
            if not password_input:
                raise GoogleOAuthError("Could not find password input field")
                
            logger.debug("Password page loaded")
            
            # Fill password
            await password_input.fill(password)
            await page.wait_for_timeout(1000)  # Small delay for form processing
            logger.debug("Password filled")
            
            # Click Next/Sign in button
            signin_selectors = ['button:has-text("Next")', '[id="passwordNext"]', 'button:has-text("Sign in")', 'button[type="submit"]']
            signin_clicked = False
            for selector in signin_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    logger.debug(f"Clicked sign-in button with selector: {selector}")
                    signin_clicked = True
                    break
                except Exception:
                    continue
            
            if not signin_clicked:
                raise GoogleOAuthError("Could not find or click sign-in button")
            
            # Wait for potential 2FA or redirect
            await page.wait_for_timeout(3000)
            
            logger.success("Google login flow completed")
            return True
            
        except GoogleOAuthError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Google login: {e}")
            raise GoogleOAuthError(f"Login failed: {e}")

    async def extract_oauth_cookies(
        self, 
        email: str, 
        password: str, 
        target_url: str,
        save_to_file: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extract OAuth cookies after completing Google OAuth flow
        
        Args:
            email: Google account email
            password: Google account password
            target_url: Target application URL
            save_to_file: Whether to save cookies to JSON file
            
        Returns:
            List of cookie dictionaries or None if failed
        """
        logger.info(f"Starting OAuth flow for {target_url}")
        logger.debug(f"Using email: {email}")
        
        async with self._get_browser_context() as (browser, context):
            try:
                page = await context.new_page()
                
                # Navigate to target app
                await page.goto(target_url, timeout=self.config.timeout, wait_until="domcontentloaded")
                logger.info(f"Navigated to {target_url}")
                
                # Find and click Google OAuth button
                google_button = await self._find_google_oauth_button(page)
                if not google_button:
                    raise GoogleOAuthError("Could not find Google OAuth button")
                
                await google_button.click()
                logger.info("Clicked Google OAuth button")
                
                # Perform Google login with retry
                login_success = await self._retry_operation(
                    self._perform_google_login, page, email, password
                )
                if not login_success:
                    raise GoogleOAuthError("Google login failed")
                
                # Wait for redirect back to target app
                parsed_url = parse_url(target_url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                await page.wait_for_url(f"{base_url}/**", timeout=self.config.timeout)
                logger.success("Redirected back to target application")
                
                # Extract all cookies and convert to dict format
                raw_cookies = await context.cookies()
                cookies = []
                for cookie in raw_cookies:
                    cookie_dict = {
                        'name': cookie.get('name', ''),
                        'value': cookie.get('value', ''),
                        'domain': cookie.get('domain', ''),
                        'path': cookie.get('path', ''),
                        'secure': cookie.get('secure', False),
                        'httpOnly': cookie.get('httpOnly', False),
                        'expires': cookie.get('expires', -1),
                        'sameSite': cookie.get('sameSite', 'Lax')
                    }
                    cookies.append(cookie_dict)
                
                logger.info(f"Extracted {len(cookies)} cookies")
                
                # Filter relevant auth cookies
                auth_keywords = ['session', 'auth', 'token', 'csrf', 'next-auth', 'access', 'jwt', 'bearer']
                relevant_cookies = []
                for cookie in cookies:
                    name = str(cookie.get('name', ''))
                    if any(keyword in name.lower() for keyword in auth_keywords):
                        relevant_cookies.append(cookie)
                
                # Log cookie information
                logger.info(f"Found {len(relevant_cookies)} relevant auth cookies:")
                for cookie in relevant_cookies:
                    name = str(cookie.get('name', 'unknown'))
                    value = str(cookie.get('value', ''))
                    display_value = value[:20] + "..." if len(value) > 20 else value
                    logger.debug(f"  {name}: {display_value}")
                
                # Save cookies to file if requested
                if save_to_file and self.config.output_dir:
                    self.config.output_dir.mkdir(exist_ok=True)
                    cookies_file = self.config.output_dir / 'oauth_cookies.json'
                    with open(cookies_file, 'w') as f:
                        json.dump(cookies, f, indent=2, default=str)
                    logger.success(f"Cookies saved to {cookies_file}")
                
                return cookies
                
            except GoogleOAuthError:
                raise
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                raise GoogleOAuthError(f"OAuth flow failed: {e}")

    async def extract_session_token(
        self, 
        email: str, 
        password: str, 
        target_url: str,
        token_names: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Extract specific session token from OAuth cookies
        
        Args:
            email: Google account email
            password: Google account password
            target_url: Target application URL
            token_names: List of token names to look for
            
        Returns:
            Session token string or None if not found
        """
        if token_names is None:
            token_names = ['next-auth.session-token', 'session-token', 'accessToken', 'access_token', 'jwt', 'bearer']
        
        try:
            cookies = await self.extract_oauth_cookies(email, password, target_url, save_to_file=False)
            if not cookies:
                return None
            
            # Search for session tokens
            for cookie in cookies:
                cookie_name = str(cookie.get('name', ''))
                if cookie_name in token_names:
                    token_value = str(cookie.get('value', ''))
                    logger.success(f"Found session token '{cookie_name}': {token_value[:20]}...")
                    return token_value
            
            logger.warning(f"No session token found matching: {token_names}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract session token: {e}")
            return None

    def format_cookies_for_curl(self, cookies: List[Dict[str, Any]]) -> str:
        """Format cookies for use in curl commands"""
        cookie_pairs = []
        for cookie in cookies:
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                cookie_pairs.append(f"{name}={value}")
        
        return "; ".join(cookie_pairs)

    async def extract_cookies_for_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Extract cookies for a specific domain"""
        if not self._context:
            logger.warning("No active browser context")
            return []
            
        try:
            all_cookies = await self._context.cookies()
            domain_cookies = []
            for cookie in all_cookies:
                cookie_dict = {
                    'name': cookie.get('name', ''),
                    'value': cookie.get('value', ''),
                    'domain': cookie.get('domain', ''),
                    'path': cookie.get('path', ''),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False),
                }
                
                cookie_domain = str(cookie_dict.get('domain', ''))
                if domain in cookie_domain or cookie_domain in domain:
                    domain_cookies.append(cookie_dict)
            
            logger.info(f"Found {len(domain_cookies)} cookies for domain {domain}")
            return domain_cookies
            
        except Exception as e:
            logger.error(f"Failed to extract domain cookies: {e}")
            return []


# Enhanced convenience functions for backward compatibility
async def google_oauth_flow(email: str, password: str, target_url: str) -> Optional[List[Dict[str, Any]]]:
    """Legacy function for backward compatibility"""
    async with GoogleOAuthClient() as client:
        return await client.extract_oauth_cookies(email, password, target_url)


async def extract_session_token(target_url: str, email: str, password: str) -> Optional[str]:
    """Legacy function for backward compatibility"""
    async with GoogleOAuthClient() as client:
        return await client.extract_session_token(email, password, target_url)


def configure_logging(level: str = "INFO", log_file: Optional[Path] = None):
    """Configure loguru logging with optimized settings"""
    logger.remove()  # Remove default handler
    
    # Console handler with colors
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # File handler if specified
    if log_file:
        log_file.parent.mkdir(exist_ok=True)
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days"
        )


async def main():
    """Example usage with improved error handling and configuration"""
    import os
    
    # Configure optimized logging
    log_dir = Path("./logs")
    configure_logging(level="INFO", log_file=log_dir / "oauth.log")
    
    # Get credentials from environment with validation
    email = os.getenv("GOOGLE_EMAIL")
    password = os.getenv("GOOGLE_PASSWORD")
    target_url = os.getenv("TARGET_URL", "https://twitterapi.io")
    
    if not email:
        logger.error("GOOGLE_EMAIL environment variable not set")
        return
    if not password:
        logger.error("GOOGLE_PASSWORD environment variable not set")
        return
    
    # Create optimized OAuth configuration
    config = OAuthConfig(
        headless=os.getenv("HEADLESS", "true").lower() == "true",
        timeout=int(os.getenv("TIMEOUT", "45000")),
        retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "./oauth_output")),
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Use async context manager for proper resource cleanup
    async with GoogleOAuthClient(config) as client:
        try:
            logger.info(f"Starting OAuth flow for {target_url}")
            start_time = time.time()
            
            # Extract session token with automatic retry
            token = await client.extract_session_token(email, password, target_url)
            
            if token:
                elapsed_time = time.time() - start_time
                logger.success(f"OAuth completed successfully in {elapsed_time:.1f}s!")
                logger.info(f"Session token: {token[:20]}...")
                
                # Extract and save all cookies for debugging
                cookies = await client.extract_oauth_cookies(email, password, target_url, save_to_file=True)
                if cookies:
                    curl_cookies = client.format_cookies_for_curl(cookies)
                    logger.info(f"Extracted {len(cookies)} total cookies")
                    
                    # Save enhanced curl example
                    if config.output_dir:
                        config.output_dir.mkdir(exist_ok=True)
                        curl_file = config.output_dir / "curl_examples.sh"
                        with open(curl_file, 'w') as f:
                            f.write(f'#!/bin/bash\n')
                            f.write(f'# Generated OAuth cookies for {target_url}\n')
                            f.write(f'# Generated on {time.strftime("%Y-%m-%d %H:%M:%S")}\n\n')
                            f.write(f'# Session API check\n')
                            f.write(f'curl -H "Cookie: {curl_cookies}" \\\n')
                            f.write(f'     -H "User-Agent: {config.user_agent}" \\\n')
                            f.write(f'     "{target_url}/api/auth/session"\n\n')
                            f.write(f'# Alternative authenticated request\n')
                            f.write(f'curl -H "Cookie: {curl_cookies}" \\\n')
                            f.write(f'     -H "User-Agent: {config.user_agent}" \\\n')
                            f.write(f'     "{target_url}/api/user/profile"\n')
                        
                        # Make executable
                        os.chmod(curl_file, 0o755)
                        logger.info(f"Enhanced curl examples saved to {curl_file}")
                        
                        # Save configuration for reuse
                        config_file = config.output_dir / "oauth_config.json"
                        with open(config_file, 'w') as f:
                            config_data = {
                                "target_url": target_url,
                                "timestamp": time.time(),
                                "success": True,
                                "token_length": len(token),
                                "cookies_count": len(cookies)
                            }
                            json.dump(config_data, f, indent=2)
                        logger.info(f"OAuth session info saved to {config_file}")
            else:
                logger.error("Failed to extract session token")
                return 1
                
        except GoogleOAuthError as e:
            logger.error(f"OAuth error: {e}")
            return 1
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code or 0)
