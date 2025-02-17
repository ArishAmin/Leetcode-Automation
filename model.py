from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import chromedriver_autoinstaller
from transformers import pipeline
import time
import random
import threading
import json
import re
import sys
import traceback
from bs4 import BeautifulSoup
import requests

class LeetCodeBot:
    def __init__(self):
        self.driver = None
        self.problem_count = 1
        self.running = False
        self.lock = threading.Lock()
        self.status = "Initialized"
        self.solved_problems = []
        self.current_problem = None
        self.is_loading = False
        try:
            self.generator = pipeline("text-generation", model="Salesforce/codegen-350M-mono")
        except Exception as e:
            print(f"Warning: Could not initialize CodeGen: {str(e)}")
            self.generator = None
        self.setup_driver()

    def setup_driver(self):
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

            chromedriver_autoinstaller.install()
            
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            self.driver.set_window_size(1920, 1080)
            
            print("✅ WebDriver started successfully")
            return True
        except Exception as e:
            error_msg = f"Error setting up driver: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.status = f"Error: {str(e)}"
            return False

    def wait_for_element(self, by, selector, timeout=10, condition="presence"):
        try:
            wait = WebDriverWait(self.driver, timeout)
            if condition == "clickable":
                return wait.until(EC.element_to_be_clickable((by, selector)))
            elif condition == "visible":
                return wait.until(EC.visibility_of_element_located((by, selector)))
            else:
                return wait.until(EC.presence_of_element_located((by, selector)))
        except Exception as e:
            print(f"Error waiting for element {selector}: {str(e)}")
            return None

    def get_random_problem(self):
        try:
            self.status = "Finding a random problem..."
            self.is_loading = True
            
            if not self.driver:
                raise Exception("WebDriver not initialized")

            # Go to problems page
            self.driver.get("https://leetcode.com/problemset/all/")
            time.sleep(3)

            # Get all problem links using JavaScript
            problems = self.driver.execute_script("""
                const rows = document.querySelectorAll('div[role="row"]');
                const problems = [];
                
                for (const row of rows) {
                    try {
                        const titleElement = row.querySelector('a[href*="/problems/"]');
                        const difficultyElement = row.querySelector('span.text-difficulty-easy, span.text-difficulty-medium, span.text-difficulty-hard');
                        
                        if (titleElement && difficultyElement) {
                            const href = titleElement.getAttribute('href');
                            const title = titleElement.textContent.trim();
                            const difficulty = difficultyElement.textContent.trim().toUpperCase();
                            
                            if (href && title && difficulty) {
                                problems.push({
                                    title: title,
                                    url: 'https://leetcode.com' + href,
                                    difficulty: difficulty
                                });
                            }
                        }
                    } catch (e) {
                        continue;
                    }
                }
                
                return problems;
            """)
            
            if not problems:
                # Try alternative selector
                problems = self.driver.execute_script("""
                    const links = document.querySelectorAll('a[href*="/problems/"]');
                    const problems = [];
                    
                    for (const link of links) {
                        try {
                            const row = link.closest('div[role="row"]');
                            if (!row) continue;
                            
                            const title = link.textContent.trim();
                            const href = link.getAttribute('href');
                            const difficultyElement = row.querySelector('span[class*="text-difficulty-"]');
                            const difficulty = difficultyElement ? difficultyElement.textContent.trim().toUpperCase() : 'MEDIUM';
                            
                            if (href && title) {
                                problems.push({
                                    title: title,
                                    url: 'https://leetcode.com' + href,
                                    difficulty: difficulty
                                });
                            }
                        } catch (e) {
                            continue;
                        }
                    }
                    
                    return problems;
                """)

            if not problems:
                raise Exception("No problems found")
            
            # Filter out premium problems and select a random one
            free_problems = [p for p in problems if not p['url'].endswith('?envType=study-plan-v2&envId=premium-algo-100')]
            if not free_problems:
                raise Exception("No free problems found")
            
            return random.choice(free_problems)

        except Exception as e:
            error_msg = f"Error getting random problem: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.status = f"Error: {str(e)}"
            return None
        finally:
            self.is_loading = False

    def get_problem_description(self):
        try:
            # Wait for the content to load
            time.sleep(3)
            
            # Try multiple approaches to get the problem description
            description = self.driver.execute_script("""
                // Try different selectors for problem description
                const selectors = [
                    'div[data-track-load="description_content"]',
                    'div[class*="description"]',
                    'div[role="tabpanel"]',
                    'div[data-cy="question-title"]',
                    'div._1l1MA' // Common LeetCode class for description
                ];
                
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        return element.textContent.trim();
                    }
                }
                
                // If no selector works, try to find any div with substantial content
                const contentDivs = Array.from(document.querySelectorAll('div')).filter(
                    div => div.textContent.length > 100 && 
                           div.textContent.includes('Example') &&
                           !div.querySelector('textarea, input')
                );
                
                return contentDivs.length > 0 ? contentDivs[0].textContent.trim() : null;
            """)
            
            if not description:
                # Fallback to BeautifulSoup if JavaScript approach fails
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                possible_containers = [
                    soup.find('div', {'data-track-load': 'description_content'}),
                    soup.find('div', {'class': lambda x: x and 'description' in x.lower()}),
                    soup.find('div', {'role': 'tabpanel'}),
                    soup.find('div', {'data-cy': 'question-title'}),
                    soup.find('div', {'class': '_1l1MA'})
                ]
                
                for container in possible_containers:
                    if container and container.get_text().strip():
                        description = container.get_text().strip()
                        break
            
            return description

        except Exception as e:
            print(f"Error getting problem description: {str(e)}")
            return None

    def solve_problem(self, problem):
        try:
            self.status = f"Solving: {problem['title']}"
            self.driver.get(problem["url"])
            time.sleep(5)

            # Select Python3 using JavaScript
            self.driver.execute_script("""
                // Try multiple approaches to select Python
                const attempts = [
                    // Try language selector button
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const langButton = buttons.find(b => 
                            b.textContent.includes('Python') || 
                            b.getAttribute('data-cy') === 'lang-select' ||
                            b.className.includes('language')
                        );
                        if (langButton) {
                            langButton.click();
                            return true;
                        }
                        return false;
                    },
                    // Try direct language selection
                    () => {
                        const pythonOption = Array.from(document.querySelectorAll('div')).find(
                            div => div.textContent.includes('Python3')
                        );
                        if (pythonOption) {
                            pythonOption.click();
                            return true;
                        }
                        return false;
                    }
                ];

                // Try each attempt
                for (const attempt of attempts) {
                    if (attempt()) break;
                }
            """)
            time.sleep(2)

            description = self.get_problem_description()
            if not description:
                raise Exception("Could not get problem description")

            solution = self.generate_solution(problem['title'], description)
            if not solution:
                raise Exception("Could not generate solution")

            # Set editor content using JavaScript
            self.driver.execute_script("""
                // Try multiple approaches to set editor content
                const setEditorContent = (content) => {
                    // Try Monaco Editor
                    try {
                        const editor = monaco.editor.getModels()[0];
                        if (editor) {
                            editor.setValue(content);
                            return true;
                        }
                    } catch (e) {}
                    
                    // Try CodeMirror
                    try {
                        const cm = document.querySelector('.CodeMirror');
                        if (cm && cm.CodeMirror) {
                            cm.CodeMirror.setValue(content);
                            return true;
                        }
                    } catch (e) {}
                    
                    // Try ace editor
                    try {
                        const ace = window.ace.edit(document.querySelector('#ace-editor'));
                        if (ace) {
                            ace.setValue(content);
                            return true;
                        }
                    } catch (e) {}
                    
                    // Try contenteditable div
                    try {
                        const editor = document.querySelector('[contenteditable="true"]');
                        if (editor) {
                            editor.textContent = content;
                            return true;
                        }
                    } catch (e) {}
                    
                    // Try textarea
                    try {
                        const textarea = document.querySelector('textarea[class*="editor"]');
                        if (textarea) {
                            textarea.value = content;
                            const event = new Event('input', { bubbles: true });
                            textarea.dispatchEvent(event);
                            return true;
                        }
                    } catch (e) {}
                    
                    return false;
                };
                
                return setEditorContent(arguments[0]);
            """, solution)
            
            time.sleep(2)

            # Submit solution using JavaScript
            self.driver.execute_script("""
                // Try multiple approaches to find and click submit button
                const attempts = [
                    // Try data-cy attribute
                    () => {
                        const button = document.querySelector('[data-cy="submit-code-btn"]');
                        if (button) {
                            button.click();
                            return true;
                        }
                        return false;
                    },
                    // Try button text content
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const submitButton = buttons.find(b => 
                            b.textContent.includes('Submit') || 
                            b.className.includes('submit')
                        );
                        if (submitButton) {
                            submitButton.click();
                            return true;
                        }
                        return false;
                    }
                ];

                // Try each attempt
                for (const attempt of attempts) {
                    if (attempt()) break;
                }
            """)
            
            time.sleep(5)

            # Check result using JavaScript
            result = self.driver.execute_script("""
                // Try multiple approaches to find success message
                const attempts = [
                    // Try success class
                    () => {
                        const element = document.querySelector('.text-success, .success');
                        return element ? element.textContent : null;
                    },
                    // Try data attributes
                    () => {
                        const element = document.querySelector('[data-state="success"]');
                        return element ? element.textContent : null;
                    },
                    // Try text content
                    () => {
                        const elements = Array.from(document.querySelectorAll('div, span'));
                        const successElement = elements.find(el => 
                            (el.textContent.includes('Accepted') || el.textContent.includes('Success')) &&
                            (el.className.includes('success') || el.className.includes('text-success'))
                        );
                        return successElement ? successElement.textContent : null;
                    }
                ];

                // Try each attempt
                for (const attempt of attempts) {
                    const result = attempt();
                    if (result) return result;
                }
                
                return null;
            """)

            if result and "Accepted" in result:
                problem["solution"] = solution
                self.solved_problems.append(problem)
                return True

            return False

        except Exception as e:
            error_msg = f"Error solving problem: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.status = f"Error: {str(e)}"
            return False

    def generate_solution(self, problem_title, description):
        try:
            if not self.generator:
                raise Exception("CodeGen not initialized")

            prompt = f"""
            # Python solution for LeetCode problem: {problem_title}
            # {description}
            
            def solution"""
            
            response = self.generator(
                prompt,
                max_length=500,
                temperature=0.7,
                top_p=0.95,
                num_return_sequences=1,
                pad_token_id=self.generator.tokenizer.eos_token_id
            )
            
            solution = response[0]['generated_text']
            solution = re.sub(r'^.*?def', 'def', solution, flags=re.DOTALL)
            return solution.strip()
        except Exception as e:
            print(f"Error generating solution: {str(e)}")
            return None

    def start_solving(self):
        solved_count = 0
        
        while self.running and solved_count < self.problem_count:
            try:
                problem = self.get_random_problem()
                if not problem:
                    self.status = "Failed to find a problem, retrying..."
                    time.sleep(5)
                    continue

                self.current_problem = problem
                
                if self.solve_problem(problem):
                    solved_count += 1
                    self.status = f"Solved {solved_count}/{self.problem_count} problems"
                else:
                    self.status = "Failed to solve problem, trying next one..."

                time.sleep(random.randint(3, 5))

            except Exception as e:
                error_msg = f"Error in solving loop: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                self.status = f"Error: {str(e)}"
                time.sleep(5)

        self.status = f"Finished solving {solved_count} problems"
        self.running = False

    def get_status(self):
        return {
            'status': self.status,
            'is_loading': self.is_loading,
            'is_running': self.running,
            'solved_problems': self.solved_problems
        }

    def get_current_problem(self):
        return self.current_problem

    def get_solved_problems(self):
        return self.solved_problems

    def stop(self):
        with self.lock:
            self.running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def set_problem_count(self, count):
        self.problem_count = count