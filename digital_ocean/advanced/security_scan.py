
"""
Polish: Usage, error handling, and onboarding comments for security_scan.py
T081: Automated security scanning of container images before deployment
Usage: python security_scan.py --image IMAGE_NAME

This script scans the specified container image for vulnerabilities before deployment.
Stub: Integrate with security scanner (e.g., Trivy, Clair) in future.
Error Handling: Prints error if image name is missing.
"""

def scan_image(image_name):
    # TODO: Integrate with Trivy/Clair for real scan
    print(f"[DRY RUN] Would scan image: {image_name}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--image":
        image = sys.argv[2]
        scan_image(image)
    else:
        print("Error: Please provide --image IMAGE_NAME")
