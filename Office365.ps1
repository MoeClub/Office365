[CmdletBinding()]
Param([String]$u, [String]$p, [String]$l, [Switch]$cn)
<#
  # Details Office365 SKU by Powershell 
  #                  Author: MoeClub.org
  
  Name       : SKU
  -------------------------------------
  E3_MSDN    : DEVELOPERPACK
  A1_Student : STANDARDWOFFPACK_STUDENT
  A1_Faculty : STANDARDWOFFPACK_FACULTY
  A1P_Student :STANDARDWOFFPACK_IW_STUDENT
  A1P_Faculty :STANDARDWOFFPACK_IW_FACULTY

#>
# Allow script: "Set-ExecutionPolicy -ExecutionPolicy Bypass -Force"

$CommandList = (Get-Command -All)
If (-Not ("Connect-MsolService" -in $CommandList.Name)) { Write-Host "`nInstall..."; Install-Module -Scope CurrentUser -Name MSOnline -Force }
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
$SecureString = ConvertTo-SecureString -AsPlainText "${Passwd}" -Force
$MySecureCreds = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList ${User},${SecureString}
Write-Host "`nLogin: ${User}"
if ($cn) {
  Connect-MsolService -Credential $MySecureCreds -AzureEnvironment AzureChinaCloud 2>&1>$null
} else {
  Connect-MsolService -Credential $MySecureCreds 2>&1>$null
}
If (-Not $?) { Write-Host "Error: Authentication."; Exit 1; }
$UserRole = (Get-MsolUserRole -UserPrincipalName "${User}").Name
$UserDetails = (Get-MsolUser -UserPrincipalName "${User}")
$UserSKU_Full = (Get-MsolAccountSku)
$UserORG = ($UserSKU_Full.AccountSkuId -Split ":")[0]
If ([String]::IsNullOrEmpty($UserORG)) { Write-Host "Error: Office365 Name." }
$UserSKU = $UserSKU_Full.AccountSkuId
If ([String]::IsNullOrEmpty($UserRole)) { $UserRole = "User" }
Write-Host "User Role: ${UserRole}"
$AdminGuid = (Get-MsolRole -RoleName "Company Administrator").ObjectId.Guid
If (-not ([String]::IsNullOrEmpty($($AdminGuid).Trim()))) {
  Function QueryAdmin($AdminUser){
    If (-not ([String]::IsNullOrEmpty($AdminUser))) {
      $AdminBlock = (Get-MsolUser -UserPrincipalName "${AdminUser}").BlockCredential
      If ("$AdminBlock" -eq "False") { $AdminStatus = "[Enable]" } Else { $AdminStatus = "[Disable]" }
      Return -Join("$AdminStatus", "$AdminUser", "; ")
    }
  }
  $AdminList = (Get-MsolRoleMember -RoleObjectId $AdminGuid).EmailAddress
  If (-not ([String]::IsNullOrEmpty($($AdminList)))) {
    $AdminRole = ""
    If ($AdminList -is [String]) {
      $AdminRole = (QueryAdmin $AdminList)
    } ElseIf ($AdminList -is [Array]) {
      For($i=0; $i -lt $AdminList.Count;$i++){
        $AdminRole += (QueryAdmin $AdminList[$i])
      }
    }
  } Else {
    $AdminRole = "[Null]"
  }
  If (-not ([String]::IsNullOrEmpty($($AdminRole)))) {
    Write-Host "Admin User: ${AdminRole}"
  }
}
$UserDomain = (Get-MsolDomain)
$UserDomain_Item = ""
For($i=0; $i -lt $UserDomain.Count; $i++) {
  $Domain_Name = $UserDomain[$i].Name
  $Domain_Default = $UserDomain[$i].IsDefault
  If ($Domain_Default -eq $True){
    $Domain_Status = "Default"
  } Else {
    $Domain_Status = $UserDomain[$i].Status
  }
  $UserDomain_Item += -Join("[", "${Domain_Status}", "]", "${Domain_Name}", "; ")
}
Write-Host "Office365 Domain: ${UserDomain_Item}"
If (-not ([String]::IsNullOrEmpty($($l).Trim()))) {
  If ("$l" -eq "_"){ Exit 0 }
  If (-Join("$UserORG", ":", "$l") -in $UserSKU) {
    $QueryItem = $l
  } Else {
    $l = ""
  }
}
If ([String]::IsNullOrEmpty($($l).Trim())) {
  $QueryItem = ""
  If ($UserSKU -is [Array]){
    If ($UserSKU.Count -gt 0) {
      $SKUITEM = ""
      For($i=0; $i -lt $UserSKU.Count; $i++){ $SKUITEM += -Join(($UserSKU[$i] -Split ":")[1], "; ") }
      Write-Host "Office365 SKU: ${SKUITEM}"
      Do { $QueryItem = (Read-Host "Query Office365 SKU") } While (-not (-Join("$UserORG", ":", "$QueryItem") -in $UserSKU))
      Write-Host "`n"
    } Else {
      Write-Host "Error: Not found subscription."; Exit 1
    }
  } Else {
    $QueryItem = ($UserSKU -Split ":")[1]
  }
}
$skuDetails = ($UserSKU_Full | where {$_.AccountSkuId -eq -Join("$UserORG", ":", "$QueryItem")})
$SubscriptionId = ($skuDetails.SubscriptionIds.Guid)
If ([String]::IsNullOrEmpty($SubscriptionId)) { Write-Host "Error: Subscription."; Exit 1 }
Function QueryStatus($SubscriptionId){
  $SubscriptionDetails = (Get-MsolSubscription -SubscriptionId $SubscriptionId)
  $SubscriptionDate = ($SubscriptionDetails.DateCreated -Split " ")[0]
  $SubscriptionStatus = "$($SubscriptionDetails.Status)"
  Write-Host "TotalUnits: $($SubscriptionDetails.TotalLicenses)"
  If ("$($SubscriptionDetails.IsTrial)" -eq "False") {
    Write-Host "SubscriptionStatus: ${SubscriptionStatus}"
  } Else {
    Write-Host "SubscriptionStatus: [Trial] ${SubscriptionStatus}"
  }
  Write-Host "SubscriptionDate: ${SubscriptionDate}"
  Write-Host "SubscriptionId: ${SubscriptionId}"
  If ("$SubscriptionStatus" -eq "Enabled") { Return 0 } Else { Return 1 }
}
$SkuPartNumber = "$($skuDetails.SkuPartNumber)"
Write-Host "SkuName: ${SkuPartNumber}"
Write-Host "ActiveUnits: $($skuDetails.ActiveUnits)"
Write-Host "ConsumedUnits: $($skuDetails.ConsumedUnits)"
If ($SubscriptionId -Is [String]) {
  $ReturnCode = (QueryStatus $SubscriptionId)
} ElseIf ($SubscriptionId -Is [Array]) {
  For($i=0;$i -lt $SubscriptionId.Count;$i++){
    Write-Host "Item: ${SkuPartNumber}[$($i+1)]"
    $ReturnList += (QueryStatus $SubscriptionId[$i])
  }
  If (1 -in $ReturnList){ $ReturnCode = 1 } Else { $ReturnCode = 0 }
}
If ("$ReturnCode" -eq "0") { Exit 0 } Else { Exit 1 }
