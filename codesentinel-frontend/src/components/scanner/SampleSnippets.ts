export interface SampleSnippet {
  title: string;
  language: string;
  category: string;
  description: string;
  code: string;
}

export const SAMPLE_SNIPPETS: SampleSnippet[] = [
  {
    title: 'CWE-89: SQL Injection (Python)',
    language: 'python',
    category: 'Vulnerable',
    description: 'Direct string interpolation of untrusted user input into raw SQL query without parameterized binding.',
    code: `def get_user_profile(db_connection, username):
    # Vulnerable: Unsanitized input concatenated directly into SQL command
    cursor = db_connection.cursor()
    query = f"SELECT id, username, email, role FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()`
  },
  {
    title: 'CWE-119: Buffer Overflow (C)',
    language: 'c',
    category: 'Vulnerable',
    description: 'Use of unsafe gets() function into fixed-size stack buffer without bounds checking.',
    code: `#include <stdio.h>
#include <string.h>

int authenticate_user() {
    char password_buffer[16];
    printf("Enter admin password: ");
    // Vulnerable: gets() does not check destination buffer boundaries
    gets(password_buffer);
    return strcmp(password_buffer, "secret") == 0;
}`
  },
  {
    title: 'CWE-79: Cross-Site Scripting (JavaScript)',
    language: 'javascript',
    category: 'Vulnerable',
    description: 'Directly injecting unsanitized URL query parameters into the DOM via innerHTML.',
    code: `function renderWelcomeBanner() {
    const urlParams = new URLSearchParams(window.location.search);
    const userGreeting = urlParams.get('name');
    
    // Vulnerable: Untrusted input rendered without contextual escaping
    document.getElementById('welcome-banner').innerHTML = 
        '<h1>Welcome back, ' + userGreeting + '!</h1>';
}`
  },
  {
    title: 'CWE-78: Command Injection (Python)',
    language: 'python',
    category: 'Vulnerable',
    description: 'Invoking system shell with unvalidated user input via os.system or subprocess shell=True.',
    code: `import os

def ping_host(user_ip):
    # Vulnerable: Allows arbitrary command chaining via ; or &&
    cmd = "ping -c 1 " + user_ip
    os.system(cmd)`
  },
  {
    title: 'Secure Parameterized Query (Python)',
    language: 'python',
    category: 'Clean',
    description: 'Safe database querying utilizing parameterized query placeholders and strict types.',
    code: `def get_user_profile_safe(db_connection, username: str):
    # Secure: Database engine escapes inputs preventing query structure modification
    cursor = db_connection.cursor()
    query = "SELECT id, username, email, role FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    return cursor.fetchone()`
  }
];
