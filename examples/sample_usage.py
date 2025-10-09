"""
Example usage of the Schedule Parser API
"""
import requests


def parse_schedule_example():
    """Example: Parse a schedule PDF and save as ICS file"""

    # API endpoint
    url = "http://localhost:8000/parse"  # For local development
    # url = "https://your-api-id.execute-api.region.amazonaws.com/prod/parse"  # For AWS API Gateway

    # File to upload
    pdf_file_path = "my_schedule.pdf"

    # Browser type (CHROME or FIREFOX)
    browser = "CHROME"

    # Prepare request
    with open(pdf_file_path, 'rb') as f:
        files = {'file': (pdf_file_path, f, 'application/pdf')}
        data = {'browser': browser}

        # Optional: Add API key for production
        # headers = {'X-API-Key': 'your-api-key-here'}

        # Make request
        response = requests.post(url, files=files, data=data)  # , headers=headers

    # Handle response
    if response.status_code == 200:
        # Save ICS file
        with open('calendar.ics', 'wb') as ics_file:
            ics_file.write(response.content)
        print("✓ Calendar generated successfully: calendar.ics")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  Message: {response.json()}")


def check_health():
    """Example: Check API health status"""
    url = "http://localhost:8000/health"
    response = requests.get(url)

    if response.status_code == 200:
        print(f"✓ Service is healthy: {response.json()}")
    else:
        print(f"✗ Service unhealthy: {response.status_code}")


def get_metrics():
    """Example: Get API metrics"""
    url = "http://localhost:8000/metrics"
    response = requests.get(url)

    if response.status_code == 200:
        metrics = response.json()
        print("📊 Metrics:")
        print(f"  Total requests: {metrics.get('requests_total', 0)}")
        print(f"  Successful: {metrics.get('requests_success', 0)}")
        print(f"  Failed: {metrics.get('requests_failed', 0)}")
        print(f"  Success rate: {metrics.get('success_rate', 0):.2f}%")
        if 'avg_processing_time_ms' in metrics:
            print(f"  Avg processing time: {metrics['avg_processing_time_ms']:.2f}ms")


def main():
    """Run examples"""
    print("Schedule Parser API Examples\n")

    # Check health
    print("1. Health Check:")
    check_health()
    print()

    # Parse schedule
    print("2. Parse Schedule:")
    # parse_schedule_example()  # Uncomment and update file path
    print("   (Commented out - update pdf_file_path first)")
    print()

    # Get metrics
    print("3. Metrics:")
    get_metrics()


if __name__ == "__main__":
    main()
