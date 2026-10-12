<!DOCTYPE html>
<html lang="en">
  <body>
    <h1>NEMO-API-Reader</h1>
    <p>A lightweight Pythong script that retrieves NEMO API data.</p>
    <h1>Prerequisites</h1>
    <ol><li>Install python3 and these packages:</li>
          <ul><li>dotenv</li>
          <li>python-dotenv</li>
          <li>requests</li></ul>
      <li>Save the .env and python files in the same directory.</li>
      <li>Create a NEMO user and ensure that it is active. A Description and/or User Type "System" may be helpful, but isn't necessary.</li>
      <li>In Detailed Administration, find User Permissions and grant "view" access to each type of desired API output.</li>
      <li>In Detailed Administration, open Tokens and add a token for your API user. Copy the Token Key.</li>
      <li>Edit the .env file to use your NEMO URL. Paste the Token Key into the API_TOKEN value.</li>
    </ol>
    <p>Your script should be ready for use and modification!</p>
    <h1>Tips for use</h1>
    It's a good idea to open your desired NEMO API via web browser, and capture the data so that you don't have to do it again.</br>
    For example, open "usage_events". Depending on your NEMO usage, this page may take a long time to load. If prompted by your browser, make it "wait for the page to respond".</br>
    When it's done loading, click the Filter button. Set a value in any field; this selection is less important than making the page load quickly.</br>
    Notice that after reloading, the page now has a string that starts, "GET /api/usage_events/". Copy this entire string to get something like this:</p>
    <code>GET /api/usage_events/?id=&id__in=&id__isnull=unknown&start__year=&start__month=&start__week=&start__second=&start__lte=&start__day=&start__hour=&start__isnull=unknown&start=&start__minute=&start__lt=&start__gt=&start__in=&start__gte=&end__year=&end__month=&end__week=&end__second=&end__lte=&end__day=&end__hour=&end__isnull=unknown&end=&end__minute=&end__lt=&end__gt=&end__in=&end__gte=&project_id=&project_id__in=&project_id__isnull=unknown&project=&project__in=&project__isnull=unknown&user_id=&user_id__in=&user_id__isnull=unknown&user=&user__in=&user__isnull=unknown&operator_id=&operator_id__in=&operator_id__isnull=unknown&operator=&operator__in=&operator__isnull=unknown&tool_id=&tool_id__in=&tool_id__isnull=unknown&tool=&tool__in=&tool__isnull=unknown&training=unknown&validated=unknown&validated_by=&validated_by__in=&validated_by__isnull=unknown&waived=unknown&waived_on__year=&waived_on__month=&waived_on__week=&waived_on__second=&waived_on__lte=&waived_on__day=&waived_on__hour=&waived_on__isnull=unknown&waived_on=&waived_on__minute=&waived_on__lt=&waived_on__gt=&waived_on__in=&waived_on__gte=&waived_by=&waived_by__in=&waived_by__isnull=unknown&note=&note__iexact=&note__in=&note__contains=&note__icontains=&note__isempty=unknown</code></p>
    The string after "/api" and before "/?" is your <strong>api_path</strong>.</br>
    Each string between "&" and "=" is a filter key.  You may need to experiment to determine the best combination of filters and values.</br>
    in prototype.py, filtered API retrieval starts around line 220, and contains several samples to get you started.</br>
  </body>
</html>
