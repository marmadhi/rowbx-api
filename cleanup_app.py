
import os

file_path = "c:\\Users\\Mathieu.MAROUFI\\AI\\rowbx-api\\app.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
found_error = False
tabs3_index = -1

# Find the valid markers
for i, line in enumerate(lines):
    if 'st.error(f"Erreur BO: {e}")' in line:
        # This is line ~369
        new_lines.append(line)
        start_delete_index = i + 1
        found_error = True
        break
    new_lines.append(line)

if not found_error:
    print("Could not find st.error marker. Aborting.")
    exit(1)

# Find where to resume (tabs[2])
resume_index = -1
for i in range(start_delete_index, len(lines)):
    if 'with tabs[2]:' in line: # Wait, searching line loop? No, accessing lines list
        pass 
        
for i in range(start_delete_index, len(lines)):
    if 'with tabs[2]:' in lines[i]:
        resume_index = i
        break

if resume_index == -1:
    print("Could not find tabs[2] marker. Aborting.")
    exit(1)

# Add some nice spacing
new_lines.append("\n")
new_lines.append("    # ========================================================================\n")
new_lines.append("    # TAB 3: TRUSTPILOT SCRAPING\n")
new_lines.append("    # ========================================================================\n")

# Copy the rest, skipping the header lines which I just added manually to be clean
# Actually tabs[2] is PRECEEDED by the header comments. 
# Better to search for the header comments of TAB 3.
# The garbage ends with `}`? 
# Let's just find `with tabs[2]:` and backtrack to the comments if possible, 
# OR just keep `with tabs[2]:` and everything after.

# Checking lines around resume_index
# lines[resume_index] is "    with tabs[2]:\n"
# lines[resume_index-1] is "    # =========..."
# lines[resume_index-2] is "    # TAB 3:..."
# lines[resume_index-3] is "    # =========..."
# If those lines exist and are NOT garbage, proper.
# But the garbage MIGHT have overwritten them?
# In Step 564, lines 580-582 seem intact.
# So I can just resume from line 580 (index 579?).

# Re-scan for the header of Tab 3
header_marker = "    # TAB 3: TRUSTPILOT SCRAPING"
header_index = -1
for i in range(start_delete_index, len(lines)):
    if header_marker in lines[i]:
        header_index = i
        break # Taking the FIRST occurrence? 
        # Wait, if I duplicated the file, maybe I have TWO Tab 3 headers?
        # The first occurrence is likely the one I want (at 581).
        # The duplicated garbage was just the BO logic block, not the Tab 3 block.
        # So finding the first Tab 3 header is correct.

if header_index != -1:
    # Just grab everything from header_index - 1 (the separator)
    resume_from = header_index - 1
    new_lines.extend(lines[resume_from:])
else:
    # Fallback to tabs[2] if header missing
    new_lines.extend(lines[resume_index:])

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Cleanup complete.")
