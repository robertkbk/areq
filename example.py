from areq import Areq
from datetime import timedelta


def main():
    areq = Areq("./proxy")
    job = areq.submit(
        "echo 'Hello world'",
        options={
            "job_name": "areq-hello-world",
            "output": "areq-hello-world",
            "nodes": 1,
            "time": timedelta(minutes=1),
            "partition": "plgrid-testing",
        },
    )

    if job["status"] != "ERROR":
        job_id = job["job_id"]

        print(f"Job submitted with ID: {job_id}")
        status = areq.status(job["job_id"])

        if status["status"] != "ERROR":
            print(f"Job {job_id} status: {status['status']}")

        else:
            print(f"Cannot get status for job {job_id}: {status['error_message']}")
    else:
        print(f"Error submitting job: {job['error_message']}")


if __name__ == "__main__":
    main()
