from final_udemy_coursefetcher import fetch_top_10_courses, fetch_top_course_link


def example_fetch_top_10():
    """Example: Fetch top 10 courses for a skill"""
    skill = "Python"
    # Example: Fetch only English courses
    language = "en"

    print(f"=== Fetching Top 10 Courses for '{skill}' (Language: {language}) ===\n")

    courses = fetch_top_10_courses(skill, language=language)

    if courses:
        print(f"Found {len(courses)} courses:\n")
        for i, course in enumerate(courses, 1):
            course_lang = "N/A"
            if "locale" in course and "locale" in course["locale"]:
                course_lang = course["locale"]["locale"]

            print(f"{i}. {course['title']}")
            print(f"   ID: {course['id']}")
            print(f"   Language: {course_lang}")
            print(f"   URL: {course.get('url', 'N/A')}\n")
    else:
        print("No courses found.")


def example_fetch_top_course_link():
    """Example: Fetch the first top course link for a skill"""
    skill = "Python"
    # Example: Fetch only Spanish courses (to test filtering)
    # or keep it as 'en' for English
    language = "en"

    print(f"\n=== Fetching Top Course Link for '{skill}' (Language: {language}) ===\n")

    course_link = fetch_top_course_link(skill, language=language)

    if course_link:
        print(f"Top course link: {course_link}")
    else:
        print("No course found.")


if __name__ == "__main__":
    # Run both examples
    example_fetch_top_course_link()
    example_fetch_top_10()
