[CmdletBinding()]
Param([String]$u, [String]$p, [String]$q, [Switch]$cn)
<#
  # Set Storage Quota for OneDrive for Busniess by Powershell 
  #                                  Author: MoeClub.org
#>

$CommandList = (Get-Command -All)
If (-Not ("Connect-MsolService" -in $CommandList.Name)) { Write-Host "`nInstall MSOnline..."; Install-Module -Scope CurrentUser -Name MSOnline -Force }
If (-Not ("Connect-SPOService" -in $CommandList.Name)) { Write-Host "`nInstall Microsoft.Online.SharePoint.PowerShell..."; Install-Module -Scope CurrentUser -Name Microsoft.Online.SharePoint.PowerShell -Force }
If ([String]::IsNullOrEmpty($($u).Trim())) { 
  Do { $User = (Read-Host "Microsoft Office365 UserName") } While ([String]::IsNullOrEmpty($($User).Trim()))
} Else {
  $User = $u
}
If ([String]::IsNullOrEmpty($($p).Trim())) { 
  Do { $Passwd = (Read-Host "Microsoft Office365 Password") } While ([String]::IsNullOrEmpty($($Passwd).Trim()))
} Else {
  $Passwd = $p
}
If ([String]::IsNullOrEmpty($($q).Trim())) { 
    $SetQuotaInt = "{0:n1}" -f 5.0
} else {
    $SetQuotaInt = [convert]::ToDouble($q)
    If (-Not $?) { Write-Host "Error: Invalid Quota."; Exit 1; }
    $SetQuotaInt = "{0:n1}" -f $SetQuotaInt
    if (${SetQuotaInt} -le ("{0:n1}" -f 0)) { Write-Host "Error: Quota must be greater than 0."; Exit 1; }
}
$SecureString = ConvertTo-SecureString -AsPlainText "${Passwd}" -Force
$MySecureCreds = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList ${User},${SecureString}
Write-Host "`nLogin: ${User}"
if ($cn) {
  Connect-MsolService -Credential $MySecureCreds -AzureEnvironment AzureChinaCloud 2>&1>$null
} else {
  Connect-MsolService -Credential $MySecureCreds 2>&1>$null
}
If (-Not $?) { Write-Host "Error: Login."; Exit 1; }
$UserORG = ((Get-MsolDomain |where { $_.IsInitial -eq $true }).Name -Split("\.", 2))[0]
if ($cn) { $EnvUrl = "sharepoint.cn" } else { $EnvUrl = "sharepoint.com" }
Connect-SPOService -Url ('https://{0}-admin.{1}' -f ($UserORG, $EnvUrl)) -Credential $MySecureCreds
If (-Not $?) { Write-Host "Error: Authentication."; Exit 1; }
$SetQuotaFlag = $false
$SetQuotaNum = 0
$StorageQuota = [Math]::floor([convert]::ToDouble(${SetQuotaInt}) * 1024 * 1024)
Do {
$SetQuotaNum += 1
Write-Host "Setting: Pre-allocation Storage Quota to ${SetQuotaInt}TB"
Set-SPOTenant -OneDriveStorageQuota $StorageQuota
$CurrentQuota = "{0:n1}" -f ((Get-SPOTenant).OneDriveStorageQuota / (1024 * 1024))
Write-Host "Current: Pre-allocation Storage Quota is ${CurrentQuota}TB"
if ($SetQuotaInt -eq $CurrentQuota){ $SetQuotaFlag = $true; break }
if ($SetQuotaNum > 7){Write-Host "Error: Current Storage Quota ${CurrentQuota}."; Exit 1;}
} while (!($SetQuotaFlag))
Write-Host "Reading: All user in [${UserORG}]"
$UserMatch = ("-my.{0}/personal/" -f ($EnvUrl))
$AllUrl = $(Get-SPOSite -IncludePersonalSite $true).Url | where { $_ -match $UserMatch }
Function SetStorage($UserUrl) {
  $CurrentUser = ([String]([String]$UserUrl -split "/")[-1] -split "_")[0]
  Write-Host "Setting: Storage Quota to ${SetQuotaInt}TB for [${CurrentUser}]"
  Set-SPOSite -StorageQuota $StorageQuota -Identity ${UserUrl}
  If ($?) {
    $UserQuota = "{0:n1}" -f ((Get-SPOSite -Identity ${UserUrl}).StorageQuota / 1024 / 1024)
    Write-Host "Current: Storage Quota is ${UserQuota}TB for [${CurrentUser}]"
  } else {
    Write-Host "Error: Storage Quota to ${SetQuotaInt}TB for [${CurrentUser}]"
  }
}
$UrlType = ($AllUrl.GetType()).Name
If ($UrlType -eq "Object[]") {
  For ($i=0; $i -lt $AllUrl.Count; $i++) {
    SetStorage $AllUrl[$i].ToString()
  }
} ElseIf ($UrlType -eq "String") {
  SetStorage $AllUrl.ToString()
}
