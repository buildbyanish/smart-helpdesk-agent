# Corvanta Technologies – IT Helpdesk FAQ

Document ID: IT-FAQ-004
Version: 4.2
Effective date: 2026-03-01
Owner: IT Service Desk
Applies to: All employees in India and Sri Lanka

The IT Service Desk supports employees in the Bengaluru (India) and Colombo (Sri Lanka) offices. Service hours are 08:00–20:00 IST/SLST, Monday to Friday. Outside these hours, only P1 incidents are handled by the on-call engineer.

Contact: helpdesk@corvanta.example · Internal extension 4357 (HELP)

---

## 1. Password Reset

### 1.1 Password rules

- Minimum length is 14 characters, with at least one upper-case letter, one number and one symbol.
- Passwords expire every 90 days. You receive reminder emails 14, 7 and 1 day before expiry.
- You cannot reuse any of your last 5 passwords.
- Your account locks for 30 minutes after 5 failed sign-in attempts.

### 1.2 Reset your password (self-service)

Use these steps if you know your current password or are enrolled in multi-factor authentication (MFA).

1. Open https://reset.corvanta.example from any browser.
2. Enter your work email address and select **Next**.
3. Approve the sign-in request in Microsoft Authenticator on your phone.
4. Enter a new password that meets the rules in section 1.1.
5. Enter the new password again to confirm it and select **Reset**.
6. Lock your laptop (Windows + L or Control + Command + Q) and sign in with the new password while connected to the office network or VPN.
7. Update the password on your phone's Outlook and Teams apps when prompted.

### 1.3 Account locked or MFA phone lost

Self-service does not work if your account is locked by Security or you no longer have your MFA phone.

1. Ask a colleague to raise a ticket for you, or call extension 4357 from an office phone.
2. Use category **access** and include your employee ID in the summary.
3. The Service Desk verifies your identity through your line manager before resetting.
4. You receive a temporary password by SMS, valid for 24 hours.
5. Sign in and change the temporary password immediately using steps 4–7 in section 1.2.

---

## 2. VPN Setup

Corvanta uses the GlobalProtect VPN client. You must be connected to the VPN to reach internal systems (PeopleHub, the finance portal and code repositories) from outside the office.

### 2.1 Install and connect on Windows

1. Open **Company Portal** from the Start menu.
2. Search for **GlobalProtect** and select **Install**. Installation takes about 3 minutes.
3. Restart your laptop when prompted.
4. Open GlobalProtect from the system tray (bottom-right of the taskbar).
5. Enter the portal address: `vpn.corvanta.example`
6. Select **Connect**.
7. Sign in with your work email and password.
8. Approve the MFA request in Microsoft Authenticator.
9. Check that the GlobalProtect icon shows a shield with a tick. You are now connected.

### 2.2 Install and connect on macOS

1. Open **Self Service** from the Applications folder.
2. Search for **GlobalProtect** and select **Install**.
3. When macOS asks, open **System Settings → Privacy & Security** and select **Allow** for the Palo Alto Networks system extension.
4. Open GlobalProtect from the menu bar.
5. Enter the portal address: `vpn.corvanta.example`
6. Sign in with your work email and password, then approve the MFA request.
7. Check that the menu bar icon shows **Connected**.

### 2.3 VPN troubleshooting

- **"Gateway not responding"**: switch from hotel or café Wi-Fi to a mobile hotspot, then reconnect. Some public networks block VPN traffic.
- **Connected but internal sites do not load**: disconnect, wait 30 seconds and reconnect. If it still fails, raise a ticket with category **network**.
- **Travelling between India and Sri Lanka**: the VPN selects the nearest gateway automatically. You do not need to change any setting.

---

## 3. Helpdesk Ticket Rules

### 3.1 When to raise a ticket

Raise a ticket for any fault, access request or hardware problem that you cannot fix using this FAQ. Do not email individual IT engineers; requests sent that way are not tracked against the SLA.

### 3.2 Categories

Choose one category per ticket:

| Category | Use for |
|---|---|
| hardware | Laptop, monitor, docking station, keyboard, mouse, headset, physical damage |
| software | Installing or fixing applications, licences, Office, Teams |
| access | Accounts, passwords, MFA, shared folders, system permissions |
| network | VPN, office Wi-Fi, internet connectivity |
| other | Anything not covered above |

### 3.3 Priority and response times

| Priority | Meaning | First response | Target resolution |
|---|---|---|---|
| P1 | Business stopped for many users, or a security incident | 15 minutes | 4 hours |
| P2 | One user fully unable to work | 1 hour | 1 business day |
| P3 | One user affected, but a workaround exists | 4 hours | 3 business days |
| P4 | Request or question | 1 business day | 5 business days |

The Service Desk sets the final priority. A broken laptop screen is normally P2 because the user cannot work without a loaner.

### 3.4 Ticket rules

1. Raise one ticket per issue. Do not combine unrelated problems.
2. Write a clear summary: what is broken, since when, and what you have already tried.
3. Do not raise a second ticket for the same issue. Add a comment to the existing ticket instead.
4. Keep your ticket ID (format `HD-` followed by digits). Quote it in any follow-up.
5. A ticket that waits for your reply for 5 business days is closed automatically.

---

## 4. Broken or Damaged Laptop

Follow these steps if your laptop is physically damaged, for example a cracked screen, broken hinge, liquid spill or keys not working.

1. Stop using the laptop if liquid has been spilled. Unplug it and do not switch it on.
2. Raise a helpdesk ticket with category **hardware**. In the summary, describe the damage and how it happened.
3. If the laptop still works, save your open work to OneDrive.
4. Take the laptop to the IT desk for inspection: **Bengaluru** – 4th Floor, Tower B; **Colombo** – Level 2, Corvanta House.
5. Collect a loaner laptop from the IT desk. Loaners are issued for up to 15 business days.
6. The IT desk confirms within 2 business days whether the laptop will be repaired or replaced.
7. Repair costs and any employee contribution are decided under section 4 of the Laptop Policy (`laptop-policy.pdf`).

Lost or stolen laptops are handled differently. See section 4.3 of the Laptop Policy.

---

## 5. Other Common Questions

### 5.1 Guest Wi-Fi

Visitors connect to **Corvanta-Guest**. Reception issues a daily code. Employees must not use the guest network for work devices.

### 5.2 Printing

Badge-release printers are on every floor. Tap your ID badge on the printer to release your job. Jobs are deleted after 24 hours.

### 5.3 Software requests

Install approved software from Company Portal (Windows) or Self Service (macOS). For software that is not listed, raise a ticket with category **software**. Your line manager must approve any paid licence.
