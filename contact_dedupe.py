import vobject
import argparse
import sys
import phonenumbers

def normalize_phone(phone_str, country_code):
    """
    Cleans spaces and converts local formats (0...) to international (+49...).
    Returns E.164 format or stripped string if parsing fails.
    """
    if not phone_str:
        return ""

    # Remove all spaces, dashes, and parens immediately
    clean_str = "".join(filter(str.isdigit, phone_str))
    if phone_str.startswith('+'):
        clean_str = '+' + clean_str

    try:
        parsed = phonenumbers.parse(phone_str, country_code)
        if phonenumbers.is_possible_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass

    return clean_str

def merge_vcf(input_file, output_file, country_code):
    contacts = {}

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            vcard_data = f.read()

        for vcard in vobject.readComponents(vcard_data):
            name = vcard.fn.value.strip() if hasattr(vcard, 'fn') else None
            if not name:
                continue

            if name not in contacts:
                # First time seeing this name, normalize its existing numbers
                if hasattr(vcard, 'tel'):
                    for tel in vcard.tel_list:
                        tel.value = normalize_phone(tel.value, country_code)
                contacts[name] = vcard
            else:
                existing_vcard = contacts[name]

                # --- Merge & Normalize Phone Numbers ---
                if hasattr(vcard, 'tel'):
                    # Get set of already normalized numbers in the master contact
                    existing_nums = {t.value for t in existing_vcard.tel_list}

                    for tel in vcard.tel_list:
                        norm_num = normalize_phone(tel.value, country_code)
                        if norm_num and norm_num not in existing_nums:
                            existing_vcard.add('tel').value = norm_num
                            existing_nums.add(norm_num) # Update set for next iteration

                # --- Merge Email Addresses ---
                if hasattr(vcard, 'email'):
                    existing_emails = {e.value.strip().lower() for e in existing_vcard.email_list} if hasattr(existing_vcard, 'email') else set()
                    for email in vcard.email_list:
                        clean_email = email.value.strip().lower()
                        if clean_email not in existing_emails:
                            existing_vcard.add('email').value = email.value.strip()
                            existing_emails.add(clean_email)

                # --- Merge Birthday ---
                if hasattr(vcard, 'bday') and not hasattr(existing_vcard, 'bday'):
                    existing_vcard.add('bday').value = vcard.bday.value

        with open(output_file, 'w', encoding='utf-8') as f:
            for name in contacts:
                f.write(contacts[name].serialize())

        print(f"Success! {len(contacts)} unique contacts written to '{output_file}'")

    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge VCF contacts with strict phone normalization.")
    parser.add_argument("input", help="Path to input .vcf file")
    parser.add_argument("-o", "--output", default="merged_contacts.vcf", help="Output file path")
    parser.add_argument("-c", "--country", default="DE", help="ISO country code (default: DE)")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    merge_vcf(args.input, args.output, args.country.upper())
