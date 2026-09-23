param(
    [Parameter(Mandatory = $true)][string]$PlanPath,
    [string]$ResultPath,
    [ValidateRange(1, 3600)][int]$TimeoutSeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

$resolvedPlan = (Resolve-Path -LiteralPath $PlanPath).Path
$planText = Get-Content -LiteralPath $resolvedPlan -Raw -Encoding UTF8

[xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="Auto Flex - Experiment Plan Review" Width="900" Height="720"
        WindowStartupLocation="CenterScreen" Topmost="True">
  <Grid Margin="14">
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="120"/>
      <RowDefinition Height="Auto"/>
    </Grid.RowDefinitions>
    <TextBlock Grid.Row="0" Margin="0,0,0,8" FontSize="16" FontWeight="SemiBold"
               Text="Review the plan below. Confirm it or submit revision feedback. The countdown auto-confirms the plan."/>
    <TextBox Name="PlanBox" Grid.Row="1" IsReadOnly="True" TextWrapping="Wrap"
             VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto"
             FontFamily="Consolas" FontSize="13"/>
    <TextBlock Grid.Row="2" Margin="0,10,0,6" FontWeight="SemiBold" Text="Revision feedback (required when submitting changes)"/>
    <TextBox Name="FeedbackBox" Grid.Row="3" AcceptsReturn="True" TextWrapping="Wrap"
             VerticalScrollBarVisibility="Auto" FontSize="13"/>
    <StackPanel Grid.Row="4" Margin="0,12,0,0" Orientation="Horizontal" HorizontalAlignment="Right">
      <Button Name="ReviseButton" Width="140" Height="34" Margin="0,0,10,0" Content="Submit revision"/>
      <Button Name="ConfirmButton" Width="180" Height="34" IsDefault="True"/>
    </StackPanel>
  </Grid>
</Window>
'@

$reader = [System.Xml.XmlNodeReader]::new($xaml)
$window = [Windows.Markup.XamlReader]::Load($reader)
$planBox = $window.FindName('PlanBox')
$feedbackBox = $window.FindName('FeedbackBox')
$reviseButton = $window.FindName('ReviseButton')
$confirmButton = $window.FindName('ConfirmButton')
$planBox.Text = $planText

$script:remaining = $TimeoutSeconds
$script:result = $null
$confirmButton.Content = "Confirm and continue ($($script:remaining)s)"
$timer = [System.Windows.Threading.DispatcherTimer]::new()
$timer.Interval = [TimeSpan]::FromSeconds(1)
$timer.Add_Tick({
    $script:remaining--
    $confirmButton.Content = "Confirm and continue ($($script:remaining)s)"
    if ($script:remaining -le 0) {
        $timer.Stop()
        $script:result = [ordered]@{ status = 'confirmed'; source = 'timeout'; feedback = ''; plan = $resolvedPlan }
        $window.DialogResult = $true
        $window.Close()
    }
})

$confirmButton.Add_Click({
    $timer.Stop()
    $script:result = [ordered]@{ status = 'confirmed'; source = 'button'; feedback = ''; plan = $resolvedPlan }
    $window.DialogResult = $true
    $window.Close()
})

$reviseButton.Add_Click({
    $feedback = $feedbackBox.Text.Trim()
    if ([string]::IsNullOrWhiteSpace($feedback)) {
        [System.Windows.MessageBox]::Show('Enter revision feedback before submitting.', 'Auto Flex') | Out-Null
        return
    }
    $timer.Stop()
    $script:result = [ordered]@{ status = 'revise'; source = 'button'; feedback = $feedback; plan = $resolvedPlan }
    $window.DialogResult = $false
    $window.Close()
})

$window.Add_Closed({
    $timer.Stop()
    if ($null -eq $script:result) {
        $script:result = [ordered]@{ status = 'cancelled'; source = 'window_closed'; feedback = ''; plan = $resolvedPlan }
    }
})

$timer.Start()
$null = $window.ShowDialog()
$json = $script:result | ConvertTo-Json -Compress
if (-not [string]::IsNullOrWhiteSpace($ResultPath)) {
    $resultDirectory = Split-Path -Parent $ResultPath
    if ($resultDirectory) { New-Item -ItemType Directory -Force -Path $resultDirectory | Out-Null }
    [System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($ResultPath), $json, [System.Text.UTF8Encoding]::new($false))
}
Write-Output $json
