@Echo OFF
title Cleaning up test artifacts...
echo "   "
rmdir claim_letters /s /q
rmdir html_reports /s /q
rmdir complete_package /s /q
rmdir test_output /s /q
rmdir pdf_reports /s /q
echo "   "
echo Cleanup complete.