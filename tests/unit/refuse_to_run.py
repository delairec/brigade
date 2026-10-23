def refuse_to_run(request):
    raise AssertionError(f"{' '.join(request.argv)} should not run")
