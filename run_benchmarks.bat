@echo off
REM Batch script to generate optimized Dockerfiles for benchmarking

REM Define directories (relative to workspace root)
SET BENCHMARK_DIR=.\testing\Dockerfiles_set
SET OUTPUT_DIR=.\testing\output

REM Ensure output directory exists
if not exist "%OUTPUT_DIR%" (
    echo Creating output directory: %OUTPUT_DIR%
    mkdir "%OUTPUT_DIR%"
)

REM --- Process Each File --  

REM File: simple_optimizable.dockerfile
echo Processing simple_optimizable.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\simple_optimizable.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-simple_optimizable.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\simple_optimizable.dockerfile" "%OUTPUT_DIR%\example1_baseline_simple_optimizable.dockerfile"

REM File: known_issues.dockerfile
echo Processing known_issues.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\known_issues.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-known_issues.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\known_issues.dockerfile" "%OUTPUT_DIR%\example1_baseline_known_issues.dockerfile"

REM File: complex_multistage.dockerfile
echo Processing complex_multistage.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\complex_multistage.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-complex_multistage.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\complex_multistage.dockerfile" "%OUTPUT_DIR%\example1_baseline_complex_multistage.dockerfile"

REM File: bad_practice_example.dockerfile
echo Processing bad_practice_example.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\bad_practice_example.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-bad_practice_example.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\bad_practice_example.dockerfile" "%OUTPUT_DIR%\example1_baseline_bad_practice_example.dockerfile"

REM File: cache_and_recommends.dockerfile
echo Processing cache_and_recommends.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\cache_and_recommends.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-cache_and_recommends.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\cache_and_recommends.dockerfile" "%OUTPUT_DIR%\example1_baseline_cache_and_recommends.dockerfile"

REM File: new_violation_apk_cache.dockerfile
echo Processing new_violation_apk_cache.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_apk_cache.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_apk_cache.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_apk_cache.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_apk_cache.dockerfile"

REM File: new_violation_expose_root.dockerfile
echo Processing new_violation_expose_root.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_expose_root.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_expose_root.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_expose_root.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_expose_root.dockerfile"

REM File: new_violation_node_npm_cache.dockerfile
echo Processing new_violation_node_npm_cache.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_node_npm_cache.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_node_npm_cache.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_node_npm_cache.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_node_npm_cache.dockerfile"

REM File: new_violation_multi_run_pip.dockerfile
echo Processing new_violation_multi_run_pip.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_multi_run_pip.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_multi_run_pip.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_multi_run_pip.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_multi_run_pip.dockerfile"

REM File: new_violation_wget_untar.dockerfile
echo Processing new_violation_wget_untar.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_wget_untar.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_wget_untar.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_wget_untar.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_wget_untar.dockerfile"

REM File: new_violation_run_cd.dockerfile
echo Processing new_violation_run_cd.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_run_cd.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_run_cd.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_run_cd.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_run_cd.dockerfile"

REM File: new_violation_apt_pinning_risk.dockerfile
echo Processing new_violation_apt_pinning_risk.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_apt_pinning_risk.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_apt_pinning_risk.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_apt_pinning_risk.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_apt_pinning_risk.dockerfile"

REM File: new_violation_no_user.dockerfile
echo Processing new_violation_no_user.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_no_user.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_no_user.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_no_user.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_no_user.dockerfile"

REM File: new_violation_update_alone.dockerfile
echo Processing new_violation_update_alone.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_update_alone.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_update_alone.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_update_alone.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_update_alone.dockerfile"

REM File: new_violation_unnecessary_package.dockerfile
echo Processing new_violation_unnecessary_package.dockerfile...
python main.py analyze "%BENCHMARK_DIR%\new_violation_unnecessary_package.dockerfile" --output-optimized-dockerfile "%OUTPUT_DIR%\optimised-new_violation_unnecessary_package.dockerfile"
python testing\openai_baseline_optimizer.py "%BENCHMARK_DIR%\new_violation_unnecessary_package.dockerfile" "%OUTPUT_DIR%\example1_baseline_new_violation_unnecessary_package.dockerfile"

echo Benchmark file generation complete.
pause 